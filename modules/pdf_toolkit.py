from __future__ import annotations

"""

AUTO-EVO-AI V0.1 — PDF 工具箱 (PyPDF2 + pdfplumber)

Grade: A (生产级) | Category: documents

职责：PDF 合并/拆分/提取/加密/解密/表单填写/旋转/压缩

"""



__module_meta__ = {

    "id": "pdf-toolkit",

    "name": "PDF Toolkit",

    "version": "V0.1",

    "group": "documents",

    "inputs": [

        {"name": "action", "type": "string", "required": True, "description": "merge / split / extract / encrypt / decrypt / rotate / fill_form / info / list"},

        {"name": "path", "type": "string", "required": False, "description": "PDF 文件路径"},

        {"name": "data", "type": "dict", "required": False, "description": "操作参数"},

    ],

    "outputs": [

        {"name": "result", "type": "dict", "description": "执行结果"},

    ],

    "triggers": [],

    "depends_on": [],

    "tags": ["adapter", "doc"],

    "grade": "A",

    "description": "PDF 全功能工具箱：合并、拆分、提取文本/表格、加密/解密、表单填写、旋转页面",

}



import os

import io

import json

import uuid

import logging

from pathlib import Path

from datetime import datetime

from typing import Any



try:

    from modules._base.enterprise_module import EnterpriseModule

    from modules._base.audit import AuditLogger

except ImportError:

    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from _base.enterprise_module import EnterpriseModule

    from _base.audit import AuditLogger



logger = logging.getLogger("evo.pdf")



# ── 依赖检查 ────────────────────────────────────────────



try:

    import PyPDF2

    HAS_PYPDF2 = True

except ImportError:

    HAS_PYPDF2 = False

    logger.warning("PyPDF2 not installed; some PDF actions disabled")



try:

    import pdfplumber

    HAS_PDFPLUMBER = True

except ImportError:

    HAS_PDFPLUMBER = False

    logger.warning("pdfplumber not installed; text/table extraction disabled")





class PdfToolkit(EnterpriseModule):

    """PDF 全功能工具箱"""



    def __init__(self, *args: Any, **kwargs: Any):

        super().__init__(*args, **kwargs)

        self._name = "pdf-toolkit"

        self._work_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "pdf")

        os.makedirs(self._work_dir, exist_ok=True)

        self._audit = AuditLogger()

        self.stats = {"calls": 0, "errors": 0}

        self._status = "ready"

        if not HAS_PYPDF2 and not HAS_PDFPLUMBER:

            self._status = "error"



    # ── 生命周期 ─────────────────────────────────────────



    def initialize(self) -> None:

        logger.info(f"[pdf-toolkit] initialized, PyPDF2={HAS_PYPDF2}, pdfplumber={HAS_PDFPLUMBER}")



    def health_check(self) -> dict[str, Any]:

        return {

            "status": self._status,

            "module": "pdf-toolkit",

            "libraries": {"PyPDF2": HAS_PYPDF2, "pdfplumber": HAS_PDFPLUMBER},

            "stats": self.stats,

        }



    def shutdown(self) -> None:

        logger.info("[pdf-toolkit] shutdown")



    # ── 主入口 ───────────────────────────────────────────



    async def execute(self, action: str, path: str = "", data: dict | None = None, **kwargs: Any) -> dict[str, Any]:

        self.stats["calls"] += 1

        data = data or {}



        action_map: dict[str, Any] = {

            "merge": self._merge_pdfs,

            "split": self._split_pdf,

            "extract_text": self._extract_text,

            "extract_tables": self._extract_tables,

            "extract_images": self._extract_images,

            "encrypt": self._encrypt_pdf,

            "decrypt": self._decrypt_pdf,

            "rotate": self._rotate_pdf,

            "fill_form": self._fill_form,

            "info": self._get_info,

            "list": self._list_pdfs,

        }

        handler = action_map.get(action)

        if not handler:

            return {"status": "error", "message": f"未知 action: {action}，可选: {list(action_map.keys())}"}

        try:

            return await handler(path, data)

        except Exception as e:

            self.stats["errors"] += 1

            logger.exception(f"[pdf] execute {action} 失败")

            return {"status": "error", "message": str(e)}



    # ── 合并 PDF ─────────────────────────────────────────



    async def _merge_pdfs(self, path: str, data: dict) -> dict[str, Any]:

        if not HAS_PYPDF2:

            return {"status": "error", "message": "PyPDF2 未安装"}

        files = data.get("files", [])

        if not files:

            return {"status": "error", "message": "未指定待合并文件列表"}



        save_path = path or os.path.join(self._work_dir, f"merged_{uuid.uuid4().hex[:8]}.pdf")

        merger = PyPDF2.PdfMerger()

        for fp in files:

            if os.path.isfile(fp):

                merger.append(fp)

        merger.write(save_path)

        merger.close()

        return {"status": "success", "path": os.path.abspath(save_path), "file_count": len(files)}



    # ── 拆分 PDF ─────────────────────────────────────────



    async def _split_pdf(self, path: str, data: dict) -> dict[str, Any]:

        if not HAS_PYPDF2:

            return {"status": "error", "message": "PyPDF2 未安装"}

        if not path or not os.path.isfile(path):

            return {"status": "error", "message": f"文件不存在: {path}"}



        ranges = data.get("ranges")  # 可选: [(1,3), (5,5)] 或 None = 每页拆

        basename = os.path.splitext(os.path.basename(path))[0]

        out_dir = data.get("output_dir", os.path.join(self._work_dir, basename))

        os.makedirs(out_dir, exist_ok=True)



        reader = PyPDF2.PdfReader(path)

        total = len(reader.pages)

        results = []



        if ranges:

            for start, end in ranges:

                writer = PyPDF2.PdfWriter()

                for i in range(start - 1, end):

                    if i < total:

                        writer.add_page(reader.pages[i])

                out_path = os.path.join(out_dir, f"{basename}_p{start}-{end}.pdf")

                with open(out_path, "wb") as f:

                    writer.write(f)

                results.append({"range": f"{start}-{end}", "path": out_path})

        else:

            for i in range(total):

                writer = PyPDF2.PdfWriter()

                writer.add_page(reader.pages[i])

                out_path = os.path.join(out_dir, f"{basename}_p{i + 1}.pdf")

                with open(out_path, "wb") as f:

                    writer.write(f)

                results.append({"page": i + 1, "path": out_path})



        return {"status": "success", "total_pages": total, "outputs": results, "output_dir": out_dir}



    # ── 提取文本 ─────────────────────────────────────────



    async def _extract_text(self, path: str, data: dict) -> dict[str, Any]:

        if not HAS_PDFPLUMBER:

            return {"status": "error", "message": "pdfplumber 未安装"}

        if not path or not os.path.isfile(path):

            return {"status": "error", "message": f"文件不存在: {path}"}



        page_range = data.get("page_range")  # (start, end) or None for all

        text_pages = {}

        full_text = []



        with pdfplumber.open(path) as pdf:

            total = len(pdf.pages)

            start = 0

            end = total

            if page_range:

                start = max(0, page_range[0] - 1)

                end = min(total, page_range[1])



            for i in range(start, end):

                page = pdf.pages[i]

                text = page.extract_text() or ""

                text_pages[i + 1] = text

                full_text.append(f"--- 第 {i + 1} 页 ---
{text}")



        result = "

".join(full_text)

        if data.get("save", False):

            txt_path = path.replace(".pdf", ".txt") if path.endswith(".pdf") else path + ".txt"

            with open(txt_path, "w", encoding="utf-8") as f:

                f.write(result)

            return {"status": "success", "path": os.path.abspath(txt_path), "pages": text_pages, "total_pages": total}



        return {"status": "success", "text": result, "pages": text_pages, "total_pages": total}



    # ── 提取表格 ─────────────────────────────────────────



    async def _extract_tables(self, path: str, data: dict) -> dict[str, Any]:

        if not HAS_PDFPLUMBER:

            return {"status": "error", "message": "pdfplumber 未安装"}

        if not path or not os.path.isfile(path):

            return {"status": "error", "message": f"文件不存在: {path}"}



        tables_data: dict[int, list[Any]] = {}

        with pdfplumber.open(path) as pdf:

            for pi, page in enumerate(pdf.pages):

                tables = page.extract_tables()

                if tables:

                    tables_data[pi + 1] = []

                    for table in tables:

                        rows = []

                        for row in table:

                            rows.append([cell.strip() if cell else "" for cell in row])

                        tables_data[pi + 1].append(rows)



        return {"status": "success", "tables": tables_data, "total_tables": sum(len(v) for v in tables_data.values())}



    # ── 提取图片 ─────────────────────────────────────────



    async def _extract_images(self, path: str, data: dict) -> dict[str, Any]:

        if not path or not os.path.isfile(path):

            return {"status": "error", "message": f"文件不存在: {path}"}



        basename = os.path.splitext(os.path.basename(path))[0]

        out_dir = data.get("output_dir", os.path.join(self._work_dir, f"{basename}_images"))

        os.makedirs(out_dir, exist_ok=True)



        extracted = []



        reader = PyPDF2.PdfReader(path)

        for pi, page in enumerate(reader.pages):

            if "/XObject" not in page["/Resources"]:

                continue

            xobj = page["/Resources"]["/XObject"]

            if not xobj:

                continue

            for obj_name in xobj:

                obj = xobj[obj_name]

                if obj["/Subtype"] == "/Image":

                    width = obj["/Width"]

                    height = obj["/Height"]

                    data_stream = obj.get_data()

                    fmt = "png"

                    if "/Filter" in obj:

                        if obj["/Filter"] == "/DCTDecode":

                            fmt = "jpg"

                        elif obj["/Filter"] == "/FlateDecode":

                            fmt = "png"

                    img_path = os.path.join(out_dir, f"page{pi + 1}_{obj_name[1:]}.{fmt}")

                    with open(img_path, "wb") as f:

                        f.write(data_stream)

                    extracted.append({"page": pi + 1, "name": str(obj_name), "size": f"{width}x{height}", "path": img_path})



        return {"status": "success", "images": extracted, "output_dir": out_dir}



    # ── 加密 PDF ─────────────────────────────────────────



    async def _encrypt_pdf(self, path: str, data: dict) -> dict[str, Any]:

        if not HAS_PYPDF2:

            return {"status": "error", "message": "PyPDF2 未安装"}

        if not path or not os.path.isfile(path):

            return {"status": "error", "message": f"文件不存在: {path}"}



        password = data.get("password", "")

        if not password:

            return {"status": "error", "message": "密码不能为空"}



        reader = PyPDF2.PdfReader(path)

        writer = PyPDF2.PdfWriter()

        for page in reader.pages:

            writer.add_page(page)

        writer.encrypt(password)



        out_path = path.replace(".pdf", "_encrypted.pdf") if path.endswith(".pdf") else path + "_encrypted.pdf"

        with open(out_path, "wb") as f:

            writer.write(f)



        return {"status": "success", "path": os.path.abspath(out_path), "original": path}



    # ── 解密 PDF ─────────────────────────────────────────



    async def _decrypt_pdf(self, path: str, data: dict) -> dict[str, Any]:

        if not HAS_PYPDF2:

            return {"status": "error", "message": "PyPDF2 未安装"}

        if not path or not os.path.isfile(path):

            return {"status": "error", "message": f"文件不存在: {path}"}



        password = data.get("password", "")

        if not password:

            return {"status": "error", "message": "密码不能为空"}



        reader = PyPDF2.PdfReader(path)

        if reader.is_encrypted:

            reader.decrypt(password)



        writer = PyPDF2.PdfWriter()

        for page in reader.pages:

            writer.add_page(page)



        out_path = path.replace("_encrypted.pdf", ".pdf").replace(".pdf", "_decrypted.pdf") if path.endswith(".pdf") else path + "_decrypted.pdf"

        with open(out_path, "wb") as f:

            writer.write(f)



        return {"status": "success", "path": os.path.abspath(out_path)}



    # ── 旋转页面 ─────────────────────────────────────────



    async def _rotate_pdf(self, path: str, data: dict) -> dict[str, Any]:

        if not HAS_PYPDF2:

            return {"status": "error", "message": "PyPDF2 未安装"}

        if not path or not os.path.isfile(path):

            return {"status": "error", "message": f"文件不存在: {path}"}



        pages = data.get("pages", [])  # [1, 3, 5] or "all"

        angle = data.get("angle", 90)  # 90 / 180 / 270



        reader = PyPDF2.PdfReader(path)

        writer = PyPDF2.PdfWriter()

        total = len(reader.pages)



        if pages == "all":

            pages = list(range(1, total + 1))



        for i in range(total):

            page = reader.pages[i]

            if (i + 1) in pages:

                page.rotate(angle)

            writer.add_page(page)



        with open(path, "wb") as f:

            writer.write(f)



        return {"status": "success", "rotated_pages": pages, "angle": angle}



    # ── 填写表单 ─────────────────────────────────────────



    async def _fill_form(self, path: str, data: dict) -> dict[str, Any]:

        if not HAS_PYPDF2:

            return {"status": "error", "message": "PyPDF2 未安装"}

        if not path or not os.path.isfile(path):

            return {"status": "error", "message": f"文件不存在: {path}"}



        field_data = data.get("fields", {})

        reader = PyPDF2.PdfReader(path)

        writer = PyPDF2.PdfWriter()



        if "/AcroForm" in reader.trailer["/Root"]:

            writer.append(reader)

            writer.update_page_form_field_values(writer.pages[0], field_data)



            out_path = path.replace(".pdf", "_filled.pdf") if path.endswith(".pdf") else path + "_filled.pdf"

            with open(out_path, "wb") as f:

                writer.write(f)

            return {"status": "success", "path": os.path.abspath(out_path), "fields_filled": len(field_data)}

        else:

            return {"status": "error", "message": "该 PDF 没有可填写表单"}



    # ── 获取信息 ─────────────────────────────────────────



    async def _get_info(self, path: str, data: dict) -> dict[str, Any]:

        if not path or not os.path.isfile(path):

            return {"status": "error", "message": f"文件不存在: {path}"}



        info: dict[str, Any] = {"file_size_bytes": os.path.getsize(path), "path": os.path.abspath(path)}



        if HAS_PYPDF2:

            reader = PyPDF2.PdfReader(path)

            info["pages"] = len(reader.pages)

            info["encrypted"] = reader.is_encrypted

            if reader.metadata:

                meta = {}

                for k, v in reader.metadata.items():

                    meta[str(k)] = str(v) if v else ""

                info["metadata"] = meta



        return {"status": "success", "info": info}



    # ── 列出 PDF 文件 ────────────────────────────────────



    async def _list_pdfs(self, path: str, data: dict) -> dict[str, Any]:

        search_dir = path or self._work_dir

        if not os.path.isdir(search_dir):

            return {"status": "error", "message": f"目录不存在: {search_dir}"}

        files = []

        for f in sorted(os.listdir(search_dir)):

            fp = os.path.join(search_dir, f)

            if os.path.isfile(fp) and f.lower().endswith(".pdf"):

                files.append({

                    "name": f,

                    "size_bytes": os.path.getsize(fp),

                    "modified": datetime.fromtimestamp(os.path.getmtime(fp)).isoformat(),

                })

        return {"status": "success", "files": files, "directory": search_dir}





module_class = PdfToolkit

