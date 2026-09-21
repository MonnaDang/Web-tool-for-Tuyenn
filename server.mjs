import { createServer } from "node:http";
import { createReadStream, createWriteStream, existsSync } from "node:fs";
import { mkdir, readFile, readdir, rm, stat, unlink } from "node:fs/promises";
import { pipeline } from "node:stream/promises";
import { Transform } from "node:stream";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(root, "public");
const storageDir = path.join(root, "storage", "jobs");
const host = "127.0.0.1";
const port = Number(process.env.PORT || 4173);
const maxUploadBytes = 32 * 1024 * 1024 * 1024;

await mkdir(storageDir, { recursive: true });

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".mp4": "video/mp4",
  ".mkv": "video/x-matroska",
  ".webm": "video/webm"
};

const ffmpegCandidates = [
  process.env.FFMPEG_PATH,
  "C:\\Program Files\\Shutter Encoder\\Library\\ffmpeg.exe",
  "C:\\Users\\chuon\\Downloads\\YoutubeDownloader.win-x86\\ffmpeg.exe",
  "C:\\Users\\chuon\\AppData\\Local\\Programs\\GNU Octave\\Octave-11.3.0\\mingw64\\bin\\ffmpeg.exe",
  "ffmpeg"
].filter(Boolean);

const ffprobeCandidates = [
  process.env.FFPROBE_PATH,
  "C:\\Program Files\\Shutter Encoder\\Library\\ffprobe.exe",
  "C:\\Users\\chuon\\AppData\\Local\\Programs\\GNU Octave\\Octave-11.3.0\\mingw64\\bin\\ffprobe.exe",
  "ffprobe"
].filter(Boolean);

function firstAvailable(candidates) {
  return candidates.find((candidate) => candidate === path.basename(candidate) || existsSync(candidate));
}

const ffmpegPath = firstAvailable(ffmpegCandidates);
const ffprobePath = firstAvailable(ffprobeCandidates);

function sendJson(response, statusCode, body) {
  response.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store"
  });
  response.end(JSON.stringify(body));
}

function safeBaseName(name) {
  const parsed = path.parse(path.basename(name || "video.mp4"));
  const stem = parsed.name
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9_-]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80) || "video";
  const extension = parsed.ext.match(/^\.[a-zA-Z0-9]{1,8}$/) ? parsed.ext.toLowerCase() : ".mp4";
  return { stem, extension };
}

function formatProcessError(stderr) {
  const usefulLines = stderr
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(-8);
  return usefulLines.join("\n") || "The video tool stopped unexpectedly.";
}

function runBinary(executable, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(executable, args, { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    const outputLimit = 4 * 1024 * 1024;

    child.stdout.on("data", (chunk) => {
      stdout = (stdout + chunk.toString()).slice(-outputLimit);
    });
    child.stderr.on("data", (chunk) => {
      stderr = (stderr + chunk.toString()).slice(-outputLimit);
    });
    child.on("error", (error) => reject(new Error(`Could not start the local video tool: ${error.message}`)));
    child.on("close", (code) => {
      if (code === 0) resolve({ stdout, stderr });
      else reject(new Error(formatProcessError(stderr)));
    });
  });
}

async function probeVideo(filePath) {
  if (!ffprobePath) throw new Error("FFprobe was not found on this computer.");
  const { stdout } = await runBinary(ffprobePath, [
    "-v", "error",
    "-show_entries", "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate",
    "-of", "json",
    filePath
  ]);
  const data = JSON.parse(stdout);
  const video = data.streams?.find((stream) => stream.codec_type === "video");
  const duration = Number(data.format?.duration);
  const size = Number(data.format?.size);

  if (!video || !Number.isFinite(duration) || duration <= 0) {
    throw new Error("This file does not contain a readable video stream.");
  }

  return {
    duration,
    size: Number.isFinite(size) ? size : (await stat(filePath)).size,
    codec: video.codec_name || "unknown",
    width: Number(video.width) || null,
    height: Number(video.height) || null,
    frameRate: video.r_frame_rate || null,
    hasAudio: data.streams?.some((stream) => stream.codec_type === "audio") || false
  };
}

async function clearParts(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  await Promise.all(entries
    .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(".mp4"))
    .map((entry) => unlink(path.join(directory, entry.name))));
}

async function listPartFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(".mp4"))
    .map((entry) => path.join(directory, entry.name))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
}

async function splitVideo({ inputPath, outputDir, stem, probe, maxBytes, trimStart, trimEnd, mode }) {
  const effectiveDuration = probe.duration - trimStart - trimEnd;
  if (effectiveDuration <= 0.05) throw new Error("The beginning and end trims remove the whole video.");

  const sourceBytesPerSecond = probe.size / probe.duration;
  let segmentSeconds = Math.min(effectiveDuration, Math.max(1, (maxBytes * 0.78) / sourceBytesPerSecond));
  let lastLargest = 0;

  for (let attempt = 0; attempt < 7; attempt += 1) {
    await clearParts(outputDir);
    const pattern = path.join(outputDir, `${stem}_part_%02d.mp4`);
    const args = ["-hide_banner", "-loglevel", "error", "-y"];

    if (mode === "precise" && trimStart > 0) args.push("-ss", String(trimStart));
    args.push("-i", inputPath);
    if (mode === "fast" && trimStart > 0) args.push("-ss", String(trimStart));
    if (effectiveDuration < probe.duration - 0.01) args.push("-t", String(effectiveDuration));
    args.push("-map", "0:v:0", "-map", "0:a?");

    if (mode === "precise") {
      args.push(
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-force_key_frames", `expr:gte(t,n_forced*${segmentSeconds.toFixed(3)})`,
        "-c:a", "aac",
        "-b:a", "128k"
      );
    } else {
      args.push("-c", "copy");
    }

    args.push(
      "-f", "segment",
      "-segment_time", segmentSeconds.toFixed(3),
      "-segment_time_delta", "0.05",
      "-segment_start_number", "1",
      "-reset_timestamps", "1",
      "-avoid_negative_ts", "make_zero",
      pattern
    );

    await runBinary(ffmpegPath, args);
    const partPaths = await listPartFiles(outputDir);
    if (!partPaths.length) throw new Error("No video parts were created.");

    const partStats = await Promise.all(partPaths.map(async (partPath) => ({
      path: partPath,
      size: (await stat(partPath)).size
    })));
    lastLargest = Math.max(...partStats.map((part) => part.size));

    if (lastLargest < maxBytes) {
      const details = [];
      for (const part of partStats) {
        const partProbe = await probeVideo(part.path);
        details.push({
          name: path.basename(part.path),
          size: part.size,
          duration: partProbe.duration
        });
      }
      return { parts: details, effectiveDuration, segmentSeconds };
    }

    if (segmentSeconds <= 1.01) break;
    const reduction = Math.min(0.82, (maxBytes / lastLargest) * 0.78);
    segmentSeconds = Math.max(1, segmentSeconds * Math.max(0.25, reduction));
  }

  if (mode === "fast") {
    throw new Error("A keyframe section is larger than the selected limit. Try Precise trim mode or choose a larger maximum size.");
  }
  throw new Error(`Could not keep every part below the selected limit. Largest attempt: ${(lastLargest / 1024 / 1024).toFixed(2)} MB.`);
}

async function saveRequestBody(request, filePath) {
  let received = 0;
  const limiter = new Transform({
    transform(chunk, _encoding, callback) {
      received += chunk.length;
      if (received > maxUploadBytes) callback(new Error("The selected file is larger than the 32 GB local limit."));
      else callback(null, chunk);
    }
  });
  await pipeline(request, limiter, createWriteStream(filePath, { flags: "wx" }));
  return received;
}

async function handleChunkRequest(request, response, url) {
  if (!ffmpegPath || !ffprobePath) {
    sendJson(response, 503, { error: "FFmpeg or FFprobe is not available. Install Shutter Encoder or set FFMPEG_PATH and FFPROBE_PATH." });
    return;
  }

  const originalName = url.searchParams.get("name") || "video.mp4";
  const maxSizeMb = Number(url.searchParams.get("maxSizeMb"));
  const trimStart = Number(url.searchParams.get("trimStart")) || 0;
  const trimEnd = Number(url.searchParams.get("trimEnd")) || 0;
  const mode = url.searchParams.get("mode") === "precise" ? "precise" : "fast";

  if (!Number.isFinite(maxSizeMb) || maxSizeMb < 1 || maxSizeMb > 2048) {
    sendJson(response, 400, { error: "Maximum part size must be between 1 and 2048 MB." });
    return;
  }
  if (trimStart < 0 || trimEnd < 0 || !Number.isFinite(trimStart) || !Number.isFinite(trimEnd)) {
    sendJson(response, 400, { error: "Trim values must be valid positive times." });
    return;
  }

  const jobId = randomUUID().replaceAll("-", "").slice(0, 12);
  const jobDir = path.join(storageDir, jobId);
  const outputDir = path.join(jobDir, "parts");
  const { stem, extension } = safeBaseName(originalName);
  const inputPath = path.join(jobDir, `source${extension}`);

  try {
    await mkdir(outputDir, { recursive: true });
    const uploadedBytes = await saveRequestBody(request, inputPath);
    if (uploadedBytes === 0) throw new Error("The selected file was empty.");

    const probe = await probeVideo(inputPath);
    const maxBytes = Math.floor(maxSizeMb * 1024 * 1024);
    const result = await splitVideo({ inputPath, outputDir, stem, probe, maxBytes, trimStart, trimEnd, mode });
    await unlink(inputPath).catch(() => {});

    sendJson(response, 200, {
      jobId,
      source: {
        name: originalName,
        duration: probe.duration,
        width: probe.width,
        height: probe.height,
        codec: probe.codec,
        hasAudio: probe.hasAudio
      },
      trimmedDuration: result.effectiveDuration,
      mode,
      maxSizeMb,
      parts: result.parts.map((part) => ({
        ...part,
        url: `/api/jobs/${jobId}/files/${encodeURIComponent(part.name)}`
      }))
    });
  } catch (error) {
    await rm(jobDir, { recursive: true, force: true }).catch(() => {});
    sendJson(response, 400, { error: error.message || "Video processing failed." });
  }
}

async function handleDownload(response, jobId, encodedName) {
  if (!/^[a-f0-9]{12}$/.test(jobId)) {
    sendJson(response, 404, { error: "Result not found." });
    return;
  }
  const name = decodeURIComponent(encodedName);
  if (name !== path.basename(name) || !name.toLowerCase().endsWith(".mp4")) {
    sendJson(response, 400, { error: "Invalid file name." });
    return;
  }
  const filePath = path.join(storageDir, jobId, "parts", name);
  try {
    const details = await stat(filePath);
    response.writeHead(200, {
      "Content-Type": "video/mp4",
      "Content-Length": details.size,
      "Content-Disposition": `attachment; filename*=UTF-8''${encodeURIComponent(name)}`,
      "Cache-Control": "private, no-store"
    });
    createReadStream(filePath).pipe(response);
  } catch {
    sendJson(response, 404, { error: "Result file not found." });
  }
}

async function serveStatic(request, response) {
  const requestPath = new URL(request.url, `http://${request.headers.host}`).pathname;
  const relativePath = requestPath === "/" ? "index.html" : requestPath.replace(/^\/+/, "");
  const filePath = path.resolve(publicDir, relativePath);

  if (!filePath.startsWith(`${publicDir}${path.sep}`) && filePath !== path.join(publicDir, "index.html")) {
    sendJson(response, 403, { error: "Forbidden" });
    return;
  }

  try {
    const details = await stat(filePath);
    if (!details.isFile()) throw new Error("Not a file");
    const contents = await readFile(filePath);
    response.writeHead(200, {
      "Content-Type": mimeTypes[path.extname(filePath).toLowerCase()] || "application/octet-stream",
      "Cache-Control": "no-store"
    });
    response.end(contents);
  } catch {
    const index = await readFile(path.join(publicDir, "index.html"));
    response.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
    response.end(index);
  }
}

const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url, `http://${request.headers.host}`);

    if (request.method === "GET" && url.pathname === "/api/health") {
      sendJson(response, 200, {
        ok: Boolean(ffmpegPath && ffprobePath),
        service: "Tuyennn Local Toolbox",
        videoTools: Boolean(ffmpegPath && ffprobePath)
      });
      return;
    }

    if (request.method === "POST" && url.pathname === "/api/chunk") {
      await handleChunkRequest(request, response, url);
      return;
    }

    const downloadMatch = url.pathname.match(/^\/api\/jobs\/([a-f0-9]{12})\/files\/([^/]+)$/);
    if (request.method === "GET" && downloadMatch) {
      await handleDownload(response, downloadMatch[1], downloadMatch[2]);
      return;
    }

    if (request.method === "DELETE" && /^\/api\/jobs\/[a-f0-9]{12}$/.test(url.pathname)) {
      const jobId = url.pathname.split("/").pop();
      await rm(path.join(storageDir, jobId), { recursive: true, force: true });
      sendJson(response, 200, { ok: true });
      return;
    }

    await serveStatic(request, response);
  } catch (error) {
    sendJson(response, 500, { error: error.message || "Unexpected local server error." });
  }
});

server.requestTimeout = 0;
server.timeout = 0;

server.listen(port, host, () => {
  console.log(`Tuyennn Local Toolbox: http://${host}:${port}`);
  console.log(`FFmpeg: ${ffmpegPath || "not found"}`);
  console.log(`FFprobe: ${ffprobePath || "not found"}`);
});

