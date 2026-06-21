#
""""""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QPainterPath


def image_provider(number, size=256) -> QImage:
    """
    Generate a placeholder QImage for a given number.
    This function is designed to be executed in a worker thread because it only operates on QImage,
    which is safe to use in a non-GUI thread in Qt5+ when painting on a QImage with
    QPainter (QImage is a paint device with a render target).

    Args:
        number: The numeric value to display in the centre of the image.
        size: Side length of the square image. Defaults to 256.

    Returns:
        A QImage filled with white and centred black text of the given number.
    """
    # This function runs in a worker thread; only touch QImage, no GUI widgets.
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.white)
    # Painting on a QImage that has a render target is thread-safe (Qt5+).
    # noinspection SpellCheckingInspection
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    font = QFont("Arial", size // 4)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("black"))
    if isinstance(number, float):
        if number.is_integer():
            text = str(int(number))
        else:
            text = f"{number:.2f}"
    else:
        text = str(number)
    painter.drawText(img.rect(), Qt.AlignCenter, text)
    painter.end()
    return img


def make_rounded_image(source: QImage, target_size: QSize, radius: int) -> QImage:
    """将源图缩放、居中裁剪到 target_size，并加上圆角，返回 ARGB32 图片。"""
    if source.isNull() or target_size.isEmpty():
        return QImage()

    # 1. 缩放（保持比例，填满目标尺寸）
    scaled = source.scaled(
        target_size,
        Qt.KeepAspectRatioByExpanding,
        Qt.SmoothTransformation,
    )

    # 2. 居中裁剪
    x = (scaled.width() - target_size.width()) // 2
    y = (scaled.height() - target_size.height()) // 2
    cropped = scaled.copy(x, y, target_size.width(), target_size.height())

    # 3. 创建透明目标图，绘制圆角路径
    result = QImage(target_size, QImage.Format_ARGB32_Premultiplied)
    result.fill(Qt.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(
        0, 0, target_size.width(), target_size.height(), radius, radius
    )
    painter.setClipPath(path)
    painter.drawImage(0, 0, cropped)
    painter.end()

    return result