import torch
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont
import os
import sys
import textwrap
import matplotlib.pyplot as plt

tiles_unicode = {
    # Manzu (characters)
    0: "\U0001F007", 1: "\U0001F008", 2: "\U0001F009", 3: "\U0001F00A", 4: "\U0001F00B",
    5: "\U0001F00C", 6: "\U0001F00D", 7: "\U0001F00E", 8: "\U0001F00F",

    # Pinzu (dots / circles)
    9: "\U0001F019", 10: "\U0001F01A", 11: "\U0001F01B", 12: "\U0001F01C", 13: "\U0001F01D",
    14: "\U0001F01E", 15: "\U0001F01F", 16: "\U0001F020", 17: "\U0001F021",

    # Souzu (bamboo)
    18: "\U0001F010", 19: "\U0001F011", 20: "\U0001F012", 21: "\U0001F013", 22: "\U0001F014",
    23: "\U0001F015", 24: "\U0001F016", 25: "\U0001F017", 26: "\U0001F018",

    # Winds
    27: "\U0001F000",  # East
    28: "\U0001F001",  # South
    29: "\U0001F002",  # West
    30: "\U0001F003",  # North

    # Dragons
    31: "\U0001F006",  # White
    32: "\U0001F005",  # Green
    33: "🀄",  # Red

    # Flowers (red set)
    34: "\U0001F022",  # Plum
    35: "\U0001F023",  # Orchid
    36: "\U0001F024",  # Bamboo
    37: "\U0001F025",  # Chrysanthemum

    # Flowers (black set / seasons)
    38: "\U0001F026",  # Spring
    39: "\U0001F027",  # Summer
    40: "\U0001F028",  # Autumn
    41: "\U0001F029",  # Winter
}


def tensor_to_tiles_string(tile_counter: torch.Tensor) -> str:
    """
    Convert a torch.Tensor([42]) tile counter into a concatenated string of Mahjong Unicode tiles.
    """
    result: list[str] = []
    for idx, count_tensor in enumerate(tile_counter):
        count: int = int(count_tensor.item())  # explicit conversion for type safety
        if count > 0:
            result.extend([tiles_unicode[idx]] * count)
    return "".join(result)

def melds_to_string(melds: List[torch.Tensor]) -> str:
    """
    Convert a list of meld tensors into a single string,
    with each meld separated by a space.
    """
    return " ".join(tensor_to_tiles_string(meld) for meld in melds)


def unicode_to_pil_image(
    text: str,
    output_path: str | None = None, 
    width: int | None = None,          
    height: int | None = None,        
    font_path: str | None= "C:/Windows/Fonts/seguisym.ttf",  
    font_size: int = 40,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    text_color: Tuple[int, int, int] = (0, 0, 0),
    auto_wrap: bool = False,
    wrap_width: int = 15,
    padding: int = 1,          # 自动大小时的边距（避免文字紧贴边缘）
    auto_size: bool = True     # 开启后，宽度和高度将自动匹配文字
) -> Image.Image:
    """
    将 Unicode 字符串绘制到 PIL 图像上。

    Args:
        auto_size (bool): 若为 True，图像尺寸将精确适配文本尺寸（忽略 width/height 参数）
        padding (int):    auto_size=True 时的内边距（像素）
        其他参数同前...
    """
    # ---------- 1. 加载字体 ----------
    font = None
    if font_path is not None:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError as e:
            raise RuntimeError(f"无法加载指定字体文件: {font_path}") from e
    else:
        candidates = []
        system = sys.platform
        if system == 'win32':
            candidates = [
                "C:/Windows/Fonts/arialuni.ttf",
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simsun.ttc",
                "C:/Windows/Fonts/STKAITI.TTF",
                "C:/Windows/Fonts/seguisym.ttf",   # 增加麻将牌支持
            ]
        elif system == 'darwin':
            candidates = [
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
            ]
        else:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            ]

        for candidate in candidates:
            if os.path.exists(candidate):
                try:
                    font = ImageFont.truetype(candidate, font_size)
                    break
                except IOError:
                    continue

        if font is None:
            try:
                font = ImageFont.load_default()
                print("警告：未找到 Unicode 字体，使用默认字体，中文可能显示为方块。")
            except:
                raise RuntimeError("无法加载任何字体，请手动提供字体路径。")

    # ---------- 2. 处理换行 ----------
    if auto_wrap:
        text = textwrap.fill(text, width=wrap_width)

    # ---------- 3. 测量文本精确尺寸 ----------
    # 创建临时绘图对象用于测量（不会影响最终图像）
    temp_img = Image.new('RGB', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    try:
        # Pillow >=8: 推荐方式，返回 (left, top, right, bottom)
        bbox = temp_draw.textbbox((0, 0), text, font=font)  # type: ignore
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        # 计算偏移量，处理字母下沉或向左突出
        offset_x = -bbox[0]
        offset_y = -bbox[1]
    except Exception:
        # 兼容旧版 Pillow / 不同 ImageDraw/ImageFont 实现
        try:
            # 尝试使用 ImageFont.getbbox
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            offset_x, offset_y = -bbox[0], -bbox[1]
        except Exception:
            try:
                # 多行文本尺寸（兼容旧 Pillow 版本）
                bbox = temp_draw.multiline_textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                offset_x, offset_y = -bbox[0], -bbox[1]
            except Exception:
                # 最后退回到简单的 textsize
                text_width, text_height = temp_draw.textsize(text, font=font) # type: ignore
                offset_x, offset_y = 0, 0
    # ---------- 4. 确定最终画布尺寸 ----------
    if auto_size:
        # 精确适配文字尺寸 + 内边距
        final_width = max(1, text_width + padding * 2)
        final_height = max(1, text_height + padding * 2)
    else:
        final_width = width if width is not None else 400
        final_height = height if height is not None else 200

    # ---------- 5. 创建最终图像并绘制 ----------
    image = Image.new('RGB', (final_width, final_height), bg_color) # type: ignore
    draw = ImageDraw.Draw(image)

    if auto_size:
        # 使用偏移量放置文字，确保所有像素（包括下沉部分）都在画布内
        draw.text((padding + offset_x, padding + offset_y), text, font=font, fill=text_color) # type: ignore
    else:
        # 固定尺寸模式下居中显示
        x = (final_width - text_width) // 2 # type: ignore
        y = (final_height - text_height) // 2 # type: ignore
        draw.text((x, y), text, font=font, fill=text_color) # type: ignore

    # ---------- 6. 保存或返回 ----------
    if output_path:
        image.save(output_path)
        print(f"图像已保存至: {output_path}")
    return image
