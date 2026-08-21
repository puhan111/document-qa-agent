"""文档解析：把 PDF / Word 转成干净的文本。"""
import pymupdf as fitz    # PyMuPDF 的导入名，用来解析 PDF
import docx    # python-docx 的导入名，用来解析 Word


def _clean(text: str) -> str:
    """清洗：去掉行尾空格和多余的空行。"""
    lines = [line.rstrip() for line in text.split("\n")]
    lines = [line for line in lines if line.strip()]
    return "\n".join(lines)


def parse_pdf(path: str) -> str:
    """解析 PDF：逐页提取文字。"""
    pdf = fitz.open(path)
    pages = [page.get_text() for page in pdf]
    pdf.close()
    return _clean("\n\n".join(pages))


def parse_docx(path: str) -> str:
    """解析 Word(.docx)：提取所有段落文字。"""
    d = docx.Document(path)
    paras = [p.text for p in d.paragraphs]
    return _clean("\n\n".join(paras))


def parse_file(path: str) -> str:
    """按文件后缀分发到对应的解析器。"""
    low = path.lower()
    if low.endswith(".pdf"):
        return parse_pdf(path)
    if low.endswith(".docx"):
        return parse_docx(path)
    raise ValueError(f"不支持的文件类型：{path}")