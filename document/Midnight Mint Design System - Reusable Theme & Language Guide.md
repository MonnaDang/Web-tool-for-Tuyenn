# Midnight Mint Design System

## 1. Purpose

This document defines the reusable visual language, interaction style, color system, typography, component behavior, and Vietnamese UI language for products made as part of the same personal ecosystem.

The goal is consistency across:

* Python desktop applications
* Web applications
* TinyPhone companion tools
* Utility applications
* Firmware configuration tools
* Future desktop or mobile interfaces

The implementation technology may change, but the visual identity and language should remain recognizable.

---

# 2. Theme Identity

## Theme Name

**Midnight Mint**

## Core Feeling

The interface should feel:

```text
calm
private
warm
modern
clean
soft
thoughtful
personal
```

It should not feel:

```text
corporate
industrial
debug-heavy
gaming-oriented
cyberpunk
neon-heavy
overly technical
overly romantic
```

The visual identity is based on:

```text
Deep navy / midnight background
+
Soft blue surfaces
+
Mint primary accent
+
Muted cool-blue secondary text
+
Very limited warm error colors
```

---

# 3. Core Visual Principle

Use a dark interface with strong hierarchy and restrained contrast.

The design should follow:

```text
Dark canvas
    ↓
Elevated dark-blue surfaces
    ↓
Soft borders
    ↓
Bright readable text
    ↓
Mint used only for important actions and active states
```

Do not use accent colors everywhere.

Mint should remain special.

Recommended distribution:

```text
70%  dark background / surfaces
20%  text / neutral interface
8%   mint accent
2%   status / warning / destructive colors
```

---

# 4. Core Color Tokens

## Background

```text
BACKGROUND_DEEP
#07111F
```

Primary application background.

Use for:

* Main window
* Page background
* Dialog background
* Large content areas

---

```text
BACKGROUND_SIDEBAR
#050E1A
```

Deeper navigation background.

Use for:

* Sidebar
* Navigation rail
* Secondary application shell

---

```text
BACKGROUND_INPUT
#061320
```

Use for:

* Text inputs
* Spin boxes
* Editable fields

---

```text
BACKGROUND_INSET
#091827
```

Use for:

* Drop zones
* Empty areas
* Embedded content
* Preview containers

---

# 5. Surface Colors

```text
SURFACE_PRIMARY
#102137
```

Main card and panel surface.

Use for:

* Main cards
* Tool cards
* Result panels
* Update panels

---

```text
SURFACE_SECONDARY
#162A42
```

Higher-contrast interactive surface.

Use for:

* Secondary buttons
* Hoverable neutral controls
* Small utility controls

---

```text
SURFACE_HOVER
#0C1B2C
```

Use for:

* Sidebar hover
* Passive navigation hover

---

```text
SURFACE_SELECTED
#0D292E
```

Use for:

* Selected navigation
* Active mint-related states

---

```text
SURFACE_MINT_SOFT
#0C262D
```

Use for:

* Selected file
* Success-adjacent cards
* Active upload item
* Connected device card

---

# 6. Primary Accent

```text
ACCENT_MINT
#5DE2C7
```

This is the primary identity color.

Use for:

* Primary buttons
* Selected navigation
* Active focus border
* Links
* Progress bars
* Successful connection indicators
* Page kicker / eyebrow text
* Active controls

Do not use it for large backgrounds.

---

## Mint Hover

```text
ACCENT_MINT_HOVER
#79EFD8
```

Use for primary button hover state.

---

## Mint Dark

```text
ACCENT_MINT_DARK
#285C5A
```

Use for disabled primary buttons.

---

## Mint Selection

```text
ACCENT_MINT_SELECTION
#245E65
```

Use for:

* Text selection
* Selected input content
* Highlight regions

---

# 7. Secondary Accent

```text
ACCENT_BLUE
#6EA8FF
```

Use sparingly.

Recommended usage:

* Number badges
* Step indicators
* Informational icons
* Secondary highlights

Do not let blue compete with mint.

Mint remains the primary product identity.

---

## Blue Badge Background

```text
ACCENT_BLUE_SURFACE
#122A47
```

## Blue Badge Border

```text
ACCENT_BLUE_BORDER
#1B3E68
```

---

# 8. Text Colors

## Primary Text

```text
TEXT_PRIMARY
#F4F8FB
```

Use for:

* Main headings
* Titles
* Important values
* Main body text

---

## Secondary Text

```text
TEXT_SECONDARY
#9FB1C2
```

Use for:

* Supporting text
* Hints
* File details
* Metadata
* Descriptions
* Secondary labels

---

## Tertiary Text

```text
TEXT_TERTIARY
#B8C6D3
```

Recommended for:

* Read-only values
* Disabled-but-readable information
* Supporting information requiring slightly more emphasis

---

## Soft Content Text

```text
TEXT_SOFT
#DCE7EF
```

Use for:

* Radio labels
* Toggle labels
* Secondary interactive text

---

# 9. Border Colors

```text
BORDER_SUBTLE
#1A2B3E
```

Use for low-emphasis structural separation.

---

```text
BORDER_STANDARD
#21364C
```

Default panel border.

---

```text
BORDER_INPUT
#263B50
```

Default input border.

---

```text
BORDER_INTERACTIVE
#2B435A
```

Interactive neutral controls.

---

```text
BORDER_DROP
#3A5268
```

Dashed drop-zone borders.

---

```text
BORDER_STRONG
#476077
```

Use for:

* Radio indicators
* Strong neutral outlines

---

# 10. Success / Connected State

Primary success states should generally reuse mint.

For subtle success surfaces:

```text
SUCCESS_BG
#0B292D
```

```text
SUCCESS_BORDER
#19504F
```

```text
SUCCESS_TEXT
#C9FFF4
```

Recommended uses:

* Device connected badge
* Successful file selection
* Ready state
* Completed operation

---

# 11. Danger / Destructive State

```text
DANGER_BG
#3B202B
```

```text
DANGER_BORDER
#63313C
```

```text
DANGER_TEXT
#FFDADD
```

Use only for:

* Delete
* Remove
* Failed operations
* Destructive confirmations

Do not use red as a decorative color.

---

# 12. Typography

## Primary Font

```text
Segoe UI
```

Recommended fallback:

```text
"Segoe UI", Inter, system-ui, sans-serif
```

The overall typography should remain clean and familiar.

---

## Typography Scale

### Page Title

```text
38 px
800 weight
```

Use for the main page title.

Example:

```text
Cập nhật TinyPhone
```

---

### Card Title

```text
19 px
700 weight
```

---

### Section Title

```text
17 px
700 weight
```

---

### Brand Title

```text
17 px
700 weight
```

---

### Body

```text
14 px
400–500 weight
```

---

### Interactive / Button

```text
14 px
700–800 weight
```

---

### Supporting Text

```text
12 px
400–600 weight
```

---

### Kicker / Eyebrow

```text
12 px
800 weight
uppercase optional
ACCENT_MINT
```

Example:

```text
TINYPHONE
```

or preferably for Vietnamese consumer interfaces:

```text
TINYPHONE CỦA CẬU
```

Do not overuse uppercase.

---

# 13. Shape Language

Use rounded corners consistently.

Recommended scale:

```text
small control       8–9 px
standard control    10–11 px
small card          13 px
drop zone           15 px
main card           17 px
status pill         14 px / pill
```

Avoid extremely rounded or bubbly layouts.

The interface should feel soft but still structured.

---

# 14. Spacing System

Use an 8 px base spacing system.

Recommended tokens:

```text
SPACE_XXS = 4 px
SPACE_XS  = 8 px
SPACE_SM  = 12 px
SPACE_MD  = 16 px
SPACE_LG  = 24 px
SPACE_XL  = 32 px
SPACE_2XL = 48 px
```

Prefer combinations of these values.

Avoid arbitrary values unless required by layout constraints.

---

# 15. Layout Principle

Every page should follow approximately:

```text
Application shell
│
├── Navigation / header
│
└── Page
     ├── Page kicker
     ├── Page title
     ├── Page description
     │
     ├── Primary content card
     ├── Secondary content
     └── Final action
```

Example:

```text
TINYPHONE

Cập nhật TinyPhone

Chọn file cập nhật và TinyPhone sẽ lo phần còn lại.

┌──────────────────────────────────────────┐
│ Chọn file                                │
│                                          │
│        Kéo file vào đây                  │
│                                          │
└──────────────────────────────────────────┘

                    [ Cập nhật TinyPhone ]
```

---

# 16. Sidebar Navigation

Sidebar should use:

```text
BACKGROUND_SIDEBAR
```

Inactive item:

```text
TEXT_SECONDARY
transparent background
```

Hover:

```text
TEXT_PRIMARY
SURFACE_HOVER
```

Active:

```text
ACCENT_MINT
SURFACE_SELECTED
subtle mint border
```

Recommended item height:

```text
44 px
```

Radius:

```text
11 px
```

Do not use icons with many unrelated colors.

Preferred icon style:

```text
single-color
outline
minimal
```

---

# 17. Primary Button

Primary actions should look unmistakably important.

Use:

```text
background: ACCENT_MINT
text: #031714
height: 48 px
radius: 11 px
font-weight: 800
```

Examples:

```text
Kết nối TinyPhone
```

```text
Cập nhật TinyPhone
```

```text
Lưu vào TinyPhone
```

```text
Thêm nhạc
```

Avoid multiple primary buttons in the same visual group.

Usually there should be only one.

---

# 18. Secondary Button

Use:

```text
SURFACE_SECONDARY
BORDER_INTERACTIVE
TEXT_PRIMARY
```

Recommended for:

```text
Chọn lại
Làm mới
Đóng
Xem trước
Đặt lại
```

---

# 19. Link Button

Use mint text without a filled background.

Examples:

```text
Xem chi tiết
```

```text
Cần trợ giúp?
```

```text
Chi tiết kỹ thuật
```

---

# 20. Destructive Button

Destructive operations should use the danger palette.

Examples:

```text
Xóa
```

```text
Gỡ khỏi TinyPhone
```

```text
Xóa dữ liệu
```

Do not use destructive colors for normal cancel actions.

---

# 21. Cards

Main cards:

```text
background: SURFACE_PRIMARY
border: BORDER_STANDARD
radius: 17 px
```

Cards should normally contain:

```text
title
optional description
content
optional action
```

Do not stack excessive nested cards.

Maximum recommended nesting:

```text
Page
└── Main card
     └── one inset area
```

---

# 22. Drop Zones

Default:

```text
BACKGROUND_INSET
BORDER_DROP
dashed border
radius 15 px
```

Drag active:

```text
background #0B232B
border ACCENT_MINT
```

User-facing text examples:

```text
Kéo file vào đây
```

```text
hoặc chọn từ máy tính
```

For photos:

```text
Kéo ảnh vào đây
hoặc chọn một tấm ảnh
```

For music:

```text
Kéo nhạc vào đây
hoặc chọn bài hát
```

---

# 23. Form Inputs

Inputs should use:

```text
BACKGROUND_INPUT
BORDER_INPUT
TEXT_PRIMARY
```

Focus:

```text
border ACCENT_MINT
```

Height:

```text
42 px
```

Radius:

```text
9 px
```

Do not use bright input backgrounds.

---

# 24. Progress Indicators

Progress should be visually quiet.

Track:

```text
#091725
```

Progress:

```text
ACCENT_MINT
```

Recommended height:

```text
9 px
```

Example:

```text
Đang cập nhật...

██████████████░░░░ 72%
```

Avoid showing detailed byte counts unless in advanced mode.

---

# 25. Status Badges

Connected / ready:

```text
SUCCESS_TEXT
SUCCESS_BG
SUCCESS_BORDER
```

Examples:

```text
● Đã kết nối
```

```text
✓ Sẵn sàng
```

Neutral:

```text
○ Chưa kết nối
```

Error:

```text
Không thể kết nối
```

Keep badge wording short.

---

# 26. Tables and Trees

Tables should avoid the traditional bright spreadsheet appearance.

Use:

```text
background: #0A1828
alternate row: #0C1C2E
border: #20364B
header: #0B1A2A
selected: #15404A
```

Recommended row height:

```text
42 px
```

Use tables only when the information genuinely benefits from columns.

For consumer-facing interfaces, prefer cards or simple lists.

---

# 27. Scrollbars

Scrollbars should remain subtle.

Track:

```text
#07111F
```

Handle:

```text
#294057
```

Width:

```text
10 px
```

Avoid highly visible scrollbars.

---

# 28. Tooltips

```text
background #13243A
border #39506A
text #F4F8FB
```

Tooltips should explain unfamiliar controls.

They should not carry critical information that is unavailable elsewhere.

---

# 29. Motion

Animations should be restrained.

Recommended duration:

```text
120–200 ms
```

Allowed:

```text
hover fade
small background transition
progress transition
small opacity changes
```

Avoid:

```text
large bouncing elements
rotating cards
excessive glow
long animations
parallax
```

The theme should feel calm.

---

# 30. Iconography

Preferred:

```text
simple
rounded
outline
single-color
```

Use:

```text
TEXT_SECONDARY
```

for inactive icons.

Use:

```text
ACCENT_MINT
```

for selected or primary icons.

Avoid emoji as core interface icons.

Small decorative `♡` may be used sparingly in personal areas.

---

# 31. Language Policy

## User-Facing Language

All normal user-facing UI must use:

```text
Vietnamese
```

This includes:

* Navigation
* Page titles
* Buttons
* Status messages
* Tooltips
* Dialogs
* Empty states
* Error messages
* Success messages
* Instructions
* Settings

---

## Internal Language

Code, identifiers, comments, logs, protocol messages, filenames, and technical documentation should use:

```text
English
```

Recommended:

```text
UI text      → Vietnamese
Code         → English
Variables    → English
Functions    → English
Comments     → English
Protocol     → English
Logs         → English
Developer UI → English or technical Vietnamese depending on context
```

---

# 32. Tone of Vietnamese UI

The language should feel:

```text
natural
gentle
short
clear
personal
non-technical
```

Avoid overly formal Vietnamese.

Prefer:

```text
Kết nối TinyPhone
```

instead of:

```text
Thiết lập kết nối thiết bị TinyPhone
```

Prefer:

```text
Thêm nhạc
```

instead of:

```text
Thêm tệp tin âm thanh
```

Prefer:

```text
Chọn ảnh
```

instead of:

```text
Lựa chọn tệp hình ảnh
```

---

# 33. Pronoun Strategy

Avoid unnecessary pronouns in general controls.

Good:

```text
Chọn ảnh
Thêm nhạc
Lưu vào TinyPhone
Thử lại
Đóng
```

For friendly supporting messages, use:

```text
cậu
```

sparingly.

Example:

```text
Một góc nhỏ dành cho những điều cậu thích.
```

Do not use `cậu` in every button or technical message.

---

# 34. Preferred Vocabulary

Use consistently:

| English / Internal | Vietnamese UI     |
| ------------------ | ----------------- |
| Home               | Trang chủ         |
| Photos             | Ảnh               |
| Music              | Nhạc              |
| Settings           | Cài đặt           |
| About              | Giới thiệu        |
| Connect            | Kết nối           |
| Disconnect         | Ngắt kết nối      |
| Connected          | Đã kết nối        |
| Disconnected       | Chưa kết nối      |
| Add                | Thêm              |
| Remove             | Xóa               |
| Replace            | Thay              |
| Change             | Thay đổi          |
| Save               | Lưu               |
| Upload             | Gửi vào TinyPhone |
| Download           | Tải xuống         |
| Retry              | Thử lại           |
| Refresh            | Làm mới           |
| Cancel             | Hủy               |
| Close              | Đóng              |
| Continue           | Tiếp tục          |
| Back               | Quay lại          |
| Next               | Tiếp theo         |
| Done               | Hoàn tất          |
| Ready              | Sẵn sàng          |
| Error              | Có lỗi xảy ra     |
| Warning            | Lưu ý             |
| Details            | Chi tiết          |
| Advanced           | Nâng cao          |
| Help               | Trợ giúp          |
| File               | File              |
| Folder             | Thư mục           |

---

# 35. Avoid Technical Vocabulary in Normal Mode

Do not expose:

```text
CRC32
RGB565
PCM16
USB CDC
baud rate
SD filename
TAR
binary
protocol
packet
filesystem
buffer
firmware validation
```

Instead translate the operation into its user intent.

Example:

Internal:

```text
CRC32 validation passed
```

UI:

```text
File đã sẵn sàng.
```

Internal:

```text
Uploading media package
```

UI:

```text
Đang gửi nhạc vào TinyPhone...
```

---

# 36. Success Messages

Keep success messages short.

Recommended:

```text
✓ Đã cập nhật TinyPhone.
```

```text
✓ Ảnh mới đã được lưu.
```

```text
✓ Đã thêm nhạc.
```

For personal products, occasional softer wording is acceptable:

```text
Ảnh mới đã có trên TinyPhone ♡
```

```text
Nhạc mới đã sẵn sàng ♡
```

Use this sparingly.

---

# 37. Error Messages

Error messages should follow:

```text
What happened
+
What the user can do
```

Example:

```text
Không thể kết nối TinyPhone.

Kiểm tra cáp USB rồi thử lại.
```

Example:

```text
Không thể mở file này.

Hãy chọn một file khác rồi thử lại.
```

Avoid:

```text
ERROR 0x31
Connection timeout
Invalid packet
```

in normal UI.

Technical details may appear under:

```text
Chi tiết kỹ thuật
```

---

# 38. Confirmation Dialogs

Confirmation copy should be direct.

Example:

```text
Xóa bài hát này?

Bài hát sẽ được xóa khỏi TinyPhone.

[ Hủy ] [ Xóa ]
```

Avoid vague confirmations:

```text
Bạn có chắc chắn muốn tiếp tục?
```

Always state what will happen.

---

# 39. Empty States

Empty states should feel warm but concise.

Photos:

```text
Chưa có ảnh nào ở đây.

Thêm một tấm ảnh cậu thích nhé.
```

Music:

```text
TinyPhone vẫn còn hơi yên tĩnh.

Thêm vài bài cậu thích nghe nhé.
```

Files:

```text
Chưa có file nào.
```

Do not use excessive emotional copy.

---

# 40. Loading States

Prefer:

```text
Đang chuẩn bị...
```

```text
Đang kết nối...
```

```text
Đang gửi vào TinyPhone...
```

```text
Sắp xong rồi...
```

Avoid showing internal processing stages unless necessary.

---

# 41. Personal Touches

The interface may contain subtle personal details.

Recommended:

```text
♡ TinyPhone
```

```text
Một góc nhỏ dành cho những điều cậu thích.
```

```text
Điều nhỏ xíu
```

```text
Ảnh mới đã có trên TinyPhone ♡
```

These should appear only in key moments.

The application should remain usable and elegant even if all personal messages are removed.

---

# 42. Branding

Recommended primary brand:

```text
TinyPhone
```

Optional mark:

```text
♡ TinyPhone
```

Supporting subtitle examples:

```text
Dành riêng cho cậu
```

```text
Một góc nhỏ của cậu
```

```text
Photos · Music · Little things
```

Avoid using technical subtitles such as:

```text
Device Manager
Firmware Utility
Media Preprocessor
SD Card Tool
```

in the normal user experience.

---

# 43. Developer / Advanced Mode

Advanced tools may expose technical terminology.

Example:

```text
Công cụ nâng cao
```

Inside it is acceptable to show:

```text
Firmware
CRC32
USB CDC
SD card
WAV
RGB565
.bin
logs
protocol status
```

The main interface and advanced interface should still share the same visual theme.

---

# 44. Theme Implementation Tokens

For implementations that support variables, use semantic names rather than literal colors.

Recommended:

```text
COLOR_BG
COLOR_BG_DEEP
COLOR_SIDEBAR

COLOR_SURFACE
COLOR_SURFACE_ALT
COLOR_SURFACE_HOVER
COLOR_SURFACE_SELECTED

COLOR_TEXT
COLOR_TEXT_MUTED
COLOR_TEXT_SOFT

COLOR_ACCENT
COLOR_ACCENT_HOVER
COLOR_ACCENT_DARK

COLOR_BLUE

COLOR_BORDER
COLOR_BORDER_INPUT
COLOR_BORDER_STRONG

COLOR_SUCCESS_BG
COLOR_SUCCESS_BORDER
COLOR_SUCCESS_TEXT

COLOR_DANGER_BG
COLOR_DANGER_BORDER
COLOR_DANGER_TEXT
```

Avoid names such as:

```text
dark_blue_1
green_2
background3
```

Semantic names make cross-platform reuse easier.

---

# 45. Canonical Theme Tokens

```text
COLOR_BG                 = #07111F
COLOR_SIDEBAR            = #050E1A
COLOR_INPUT_BG           = #061320
COLOR_INSET_BG           = #091827

COLOR_SURFACE            = #102137
COLOR_SURFACE_ALT        = #162A42
COLOR_SURFACE_HOVER      = #0C1B2C
COLOR_SURFACE_SELECTED   = #0D292E
COLOR_SURFACE_MINT       = #0C262D

COLOR_TEXT               = #F4F8FB
COLOR_TEXT_MUTED         = #9FB1C2
COLOR_TEXT_READONLY      = #B8C6D3
COLOR_TEXT_SOFT          = #DCE7EF

COLOR_ACCENT             = #5DE2C7
COLOR_ACCENT_HOVER       = #79EFD8
COLOR_ACCENT_DISABLED    = #285C5A
COLOR_ACCENT_SELECTION   = #245E65

COLOR_BLUE               = #6EA8FF
COLOR_BLUE_SURFACE       = #122A47
COLOR_BLUE_BORDER        = #1B3E68

COLOR_BORDER_SUBTLE      = #1A2B3E
COLOR_BORDER             = #21364C
COLOR_BORDER_INPUT       = #263B50
COLOR_BORDER_INTERACTIVE = #2B435A
COLOR_BORDER_DROP        = #3A5268
COLOR_BORDER_STRONG      = #476077

COLOR_SUCCESS_BG         = #0B292D
COLOR_SUCCESS_BORDER     = #19504F
COLOR_SUCCESS_TEXT       = #C9FFF4

COLOR_DANGER_BG          = #3B202B
COLOR_DANGER_BORDER      = #63313C
COLOR_DANGER_TEXT        = #FFDADD
```

---

# 46. Cross-Platform Mapping

## Python / Qt

Use QSS selectors and object names.

Example:

```text
PrimaryButton
SecondaryButton
DangerButton
Panel
Sidebar
PageTitle
Muted
StatusBadge
```

---

## Web

Convert tokens into CSS variables.

Example:

```css
:root {
    --bg: #07111f;
    --surface: #102137;
    --text: #f4f8fb;
    --muted: #9fb1c2;
    --accent: #5de2c7;
    --border: #21364c;
}
```

---

## LVGL

Use role-based constants.

Example:

```cpp
#define UI_COLOR_BG              lv_color_hex(0x07111F)
#define UI_COLOR_SURFACE         lv_color_hex(0x102137)
#define UI_COLOR_TEXT            lv_color_hex(0xF4F8FB)
#define UI_COLOR_TEXT_MUTED      lv_color_hex(0x9FB1C2)
#define UI_COLOR_ACCENT          lv_color_hex(0x5DE2C7)
#define UI_COLOR_BORDER          lv_color_hex(0x21364C)
```

Do not let platform-specific naming fragment the theme.

---

# 47. Component Consistency Rule

The same semantic element should look conceptually identical across products.

Example:

```text
PRIMARY ACTION
Python → mint QPushButton
Web    → mint primary button
LVGL   → mint button
```

```text
ACTIVE NAVIGATION
Python → dark mint surface + mint text
Web    → dark mint surface + mint text
LVGL   → dark mint surface + mint text
```

```text
CONNECTED STATUS
All platforms → subtle dark mint badge + light mint text
```

Exact pixels may differ.

The visual meaning must remain the same.

---

# 48. Do Not Copy Desktop Geometry Blindly

Theme consistency does not mean identical sizing.

Desktop:

```text
48 px primary button
38 px page title
17 px card title
```

TinyPhone LVGL may require:

```text
smaller typography
smaller radius
smaller padding
compact status areas
```

Preserve:

```text
color role
hierarchy
tone
interaction meaning
```

not exact physical dimensions.

---

# 49. Accessibility

Maintain sufficient contrast between:

```text
TEXT_PRIMARY
and
background / surfaces
```

Do not indicate state using color alone.

Examples:

Bad:

```text
green circle only
```

Better:

```text
● Đã kết nối
```

Bad:

```text
red input border only
```

Better:

```text
File này không hợp lệ.
```

---

# 50. Master Design Rule

Every future product should be recognizable as belonging to the same ecosystem even when the user does not see the product name.

Recognition should come from:

```text
deep navy canvas
+
blue layered surfaces
+
mint primary accent
+
soft cool typography
+
rounded structured cards
+
short Vietnamese copy
+
calm interaction
```

---

# 51. Quick Implementation Checklist

Before releasing a new product, verify:

* Main canvas uses Midnight Mint dark navy.
* Main cards use `#102137`.
* Primary accent is `#5DE2C7`.
* Mint is not overused.
* Primary text is near-white.
* Secondary text uses cool muted blue.
* Buttons use the shared hierarchy.
* Card radius remains soft but structured.
* User-facing interface is Vietnamese.
* Code and internal identifiers are English.
* Technical details are hidden from normal users.
* Error text explains what the user can do.
* Normal UI does not expose debug terminology.
* Personal wording is subtle.
* Only one dominant primary action appears per area.
* Product remains calm and easy to scan.

---

# 52. Visual Signature

The shortest definition of the theme is:

```text
Midnight navy.
Soft blue layers.
Mint interaction.
Cool white text.
Quiet personal language.
```

Or as a design formula:

```text
Midnight Mint
=
#07111F
+ #102137
+ #5DE2C7
+ #F4F8FB
+ #9FB1C2
+ soft rounded geometry
+ Vietnamese-first UI
```

This formula should remain the visual and language foundation for future products created for the same personal ecosystem.
