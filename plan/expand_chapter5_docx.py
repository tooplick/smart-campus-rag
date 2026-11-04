# -*- coding: utf-8 -*-
"""扩充并规范论文第5章的内容与段落格式。"""

from pathlib import Path
import shutil

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "毕业设计论文_导师修改版_目录黑色.docx"
OUTPUT = ROOT / "毕业设计论文_导师修改版_第五章扩充格式优化.docx"


CAPTIONS = {
    "图5-1 管理端登录失败提示",
    "图5-2 管理员首次改密页面",
    "图5-3 管理端文档列表页面",
    "图5-4 文档入库进度页面",
    "图5-5 聊天端问答页面",
    "图5-6 问答来源列表",
    "图5-7 引用文件预览页面",
}


REPLACEMENTS = {
    "本章按照功能页面介绍系统实现结果，重点展示实际运行截图。系统实现包括管理员登录、文档管理、聊天问答和来源预览，每项功能配一张截图并说明页面作用。": {
        "text": "第5章围绕系统已经完成并能够稳定演示的功能页面展开，重点说明前端界面、交互反馈以及后端处理结果在页面中的呈现方式。与前文的需求分析和总体设计相比，本章更加关注功能是否真正落地，以及用户在实际使用过程中能够看到什么、如何操作以及系统会给出怎样的响应。",
        "after": [
            "本章的展示内容按照实际使用流程组织，先说明管理员进入系统后的身份校验与初始化操作，再介绍文档入库管理过程，随后展示聊天问答与来源核验功能。这样的安排能够把“后台管理—知识入库—前台问答—结果溯源”串联起来，体现系统从资料维护到用户查询的完整运行链路。"
        ],
    },
    "管理员通过登录页面进入系统。系统只有一个管理员账户，登录时校验用户名和密码；密码错误时不进入管理页面，并在页面上给出提示。": {
        "text": "管理员通过登录页面进入系统，页面提供用户名和密码输入框，并对必填项进行前端校验。当输入内容为空或不符合要求时，界面会在字段附近给出提示信息，同时通过顶部消息提醒用户当前的输入问题，从而减少重复提交带来的操作成本。",
        "after": [
            "在登录交互上，系统还提供密码显隐切换，便于管理员在不同设备环境下核对输入内容。提交成功后，系统会根据账户状态判断是否需要执行首次改密；若认证失败，则保持当前页面不跳转，并保留输入表单供管理员继续修正。"
        ],
    },
    "图5-1展示了输入错误密码后的登录页面，顶部提示“用户名或密码错误”，登录表单仍然保留，管理员可以重新输入凭证。": {
        "text": "从图5-1可以看出，当管理员输入错误密码后，页面会明确反馈“用户名或密码错误”，并保留原有登录表单结构。这样的处理方式避免了页面刷新后信息丢失，有助于管理员快速重新输入正确凭证，也体现出系统在身份认证环节对可用性和操作连续性的考虑。"
    },
    "首次登录时，管理员还需要完成密码初始化。图5-2展示了输入新密码和确认密码的页面，修改成功后才能进入管理功能。": {
        "text": "为了避免默认密码长期保留带来的安全隐患，系统在管理员首次登录后要求立即完成密码初始化。该页面除了录入当前密码外，还要求填写新密码和确认密码，并对新密码长度以及两次输入一致性进行实时校验，确保初始化结果符合基本的安全要求。",
        "after": [
            "只有当全部校验通过后，系统才会提交初始化请求并允许管理员进入仪表盘页面。这样一来，系统在管理入口就建立了最基本的口令更新机制，使后续的文档管理和知识库维护建立在更可靠的账户安全基础之上。"
        ],
    },
    "管理员登录后可以进入文档管理页面，选择知识库并上传文件。系统支持 PDF、DOCX、TXT、Markdown、CSV、XLSX、PPTX、HTML 和图片等格式，上传后由后台任务处理。": {
        "text": "文档管理页面是知识库维护的核心入口，管理员在该页面可以先选择目标知识库，再执行文件上传和状态查看等操作。系统支持 PDF、DOCX、TXT、Markdown、CSV、XLSX、PPTX、HTML 以及图片等多种格式，能够覆盖校园场景中常见的规章制度、通知公告、课表清单和业务表格等资料来源。",
        "after": [
            "上传动作发起后，前端并不直接等待全部处理完成，而是把任务交由后端异步执行。这样既能减少管理员在页面上的阻塞等待，也便于系统对解析、切片、向量化和入库等环节进行分步处理，使文档导入流程更适合实际批量维护场景。"
        ],
    },
    "图5-3展示了文档列表页面，列表中显示文件名、文件大小、切片数量、处理状态、进度、创建时间和操作按钮，管理员可以在同一页面查看文档当前状态。": {
        "text": "结合图5-3可以看到，文档列表集中展示了文件名、文件大小、切片数量、处理状态、处理进度、创建时间和操作按钮等信息。管理员不需要在多个页面之间切换，就能判断文档是否已经完成入库、是否需要重新处理，以及当前知识库中的资料维护情况，从而提升后台管理的效率。"
    },
    "文档上传后由后台任务依次处理。图5-4展示了文档列表中的处理状态，管理员可以根据状态和进度判断文件是否正在排队或处理。": {
        "text": "文档上传完成后，系统会按照既定流程依次执行解析、切片、向量化与存储等后台任务。在这一过程中，前端通过轮询机制持续刷新列表状态，使管理员能够及时了解文档是否处于待处理、处理中、已完成或失败等不同阶段，而不必依赖手动反复刷新页面。",
        "after": [
            "当文档处理失败时，页面会保留错误信息和再次处理入口；当文档仍在处理中时，系统会限制删除等不合时宜的操作，避免因为误操作破坏正在执行的任务。这样的状态控制使文档入库过程更加清晰，也更符合实际管理场景中的稳定性要求。"
        ],
    },
    "用户进入聊天页面后，系统为其生成匿名客户端标识，不要求注册。用户在输入框中提交问题，系统从已完成入库的知识切片中检索相关内容，再调用生成模型组织回答。图5-5展示了聊天页面中的问答结果，用户问题位于页面右上方，回答区域按段落显示与图书馆借阅规则有关的内容，回答中的重点信息得到突出显示。": {
        "text": "聊天问答页面是系统面向普通用户的核心使用界面。用户进入页面后，系统会自动创建匿名会话标识，无需额外注册即可直接提问。提交问题后，系统会先从已经完成入库的知识切片中执行检索，再把检索结果交给生成模型组织自然语言回答，从而实现基于校内资料的问答服务。",
        "after": [
            "前端界面采用通栏消息流布局，用户问题与系统回答按对话顺序排列，便于连续阅读和多轮追问。与此同时，会话记录会被保存到会话列表中，用户后续可以继续打开历史对话查看既有内容，这使系统不仅能完成一次性问答，也具备持续对话的基本能力。"
        ],
    },
    "回答采用流式方式返回，文本随着模型生成逐步显示，用户可以在等待完整回答前看到已经生成的内容。": {
        "text": "从图5-5展示的界面效果可以看出，系统回答采用流式方式逐步返回，文本会随着模型生成过程持续追加到消息区域。相较于一次性等待完整结果后再显示，这种方式能够更快给用户反馈，缩短等待过程中的空白感，也更符合问答系统的即时交互特征。"
    },
    "回答生成后，系统在消息下方列出本次回答使用的参考来源。来源卡片显示文件名、命中来源数量和相似度，用户可以据此判断回答来自哪些资料。": {
        "text": "为了让回答结果具备可追溯性，系统在生成回答后会同步展示本次回答所引用的参考来源。来源卡片以文件为单位进行聚合，页面中不仅展示文件名，还会给出命中来源数量、页码信息和相似度结果，帮助用户快速判断答案主要来自哪些资料。",
        "after": [
            "这种来源展示方式把“回答内容”和“证据材料”同时呈现在同一条消息之下，使用户无需离开当前问答场景就能初步完成可信度判断。对于校园制度、借阅规则、奖学金评定等需要依据原始文件核实的应用场景而言，这一设计能够明显增强系统回答的解释性。"
        ],
    },
    "图5-6展示了来源列表，本次回答对应了图书馆借阅规则、教室借用管理办法和奖学金评定标准等文件。": {
        "text": "从图5-6可以看出，一次回答可能同时关联多个来源文件，例如图书馆借阅规则、教室借用管理办法和奖学金评定标准等资料都会在列表中展示出来。通过这种多来源并列显示方式，系统能够把回答背后的证据范围更完整地暴露给用户，避免结果只停留在单一文本片段层面。"
    },
    "用户点击来源卡片后可以打开原始文件预览。图5-7展示了预览窗口中的文件名和原始内容，用户可以直接核对回答依据。": {
        "text": "当用户需要进一步核对回答依据时，可以直接点击来源卡片打开原始文件预览窗口。预览组件会根据文件类型采用不同展示方式，例如文本类文件直接显示原文内容，图片类文件展示原图，浏览器不便内联展示的格式则提供下载查看入口，以保证核验链路能够顺畅完成。",
        "after": [
            "预览窗口中会显示文件名以及对应的原始内容区域，用户可以在阅读回答之后立即对照原文进行检查。这样一来，系统不仅给出答案，还给出了核验答案的具体入口，使“可回答”进一步转化为“可验证”。"
        ],
    },
    "通过来源列表和原文预览，系统把回答内容与实际资料连接起来。用户可以先阅读回答，再点击来源核对原文；当知识库中没有达到阈值的相关切片时，系统返回拒答提示，不依据模型自身知识补写答案。": {
        "text": "通过来源列表和原文预览两个环节，系统把生成式回答与知识库中的实际资料建立了明确关联。用户既可以先阅读整理后的自然语言答案，也可以继续打开来源文件查看原始依据，从而形成“回答生成—证据展示—原文核查”的完整闭环。",
        "after": [
            "当知识库中未检索到满足阈值要求的相关切片时，系统会返回拒答或提示信息，而不是依赖模型自身的泛化知识进行补写。这一处理策略体现了系统以校内资料为核心的数据边界意识，有助于降低无依据回答带来的使用风险。"
        ],
    },
    "本章以系统实际运行页面为依据，介绍了管理员登录与首次改密、文档管理、文档入库进度、聊天问答、来源列表和原文预览功能。截图展示了系统从文档管理到知识问答的主要操作结果，第6章将进一步说明测试环境、测试用例和测试结果。": {
        "text": "本章结合系统实际运行页面，对管理员登录与首次改密、文档管理、文档入库进度、聊天问答、来源列表以及原文预览等功能进行了说明。可以看出，系统已经形成了较为完整的业务闭环：管理员负责资料维护和入库处理，普通用户负责查询与核验，前后台功能之间衔接清晰，能够支持智能校园知识库的基本使用需求。",
        "after": [
            "通过这些实现页面的展示，前文提出的功能需求已经转化为可操作、可观察的界面结果。下一章将在此基础上进一步说明系统测试环境、测试用例和测试结果，以验证各项功能在实际运行中的正确性与稳定性。"
        ],
    },
}


def set_font(run, east="宋体", size=12, bold=False, ascii_font=None):
    ascii_font = ascii_font or east
    run.font.name = ascii_font
    run.font.size = Pt(size)
    run.bold = bold
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:eastAsia"), east)
    r_fonts.set(qn("w:ascii"), ascii_font)
    r_fonts.set(qn("w:hAnsi"), ascii_font)


def set_body_format(paragraph):
    paragraph.alignment = None
    pf = paragraph.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(24)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.first_line_indent = Pt(24)


def set_caption_format(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = paragraph.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(18)
    pf.space_before = Pt(6)
    pf.space_after = Pt(3)
    pf.first_line_indent = Pt(0)


def clear_paragraph(paragraph):
    for child in list(paragraph._p):
        if child.tag.endswith("}pPr"):
            continue
        paragraph._p.remove(child)


def write_body(paragraph, text):
    clear_paragraph(paragraph)
    set_body_format(paragraph)
    run = paragraph.add_run(text)
    set_font(run, east="宋体", size=12, ascii_font="Times New Roman")


def write_caption(paragraph, text):
    clear_paragraph(paragraph)
    set_caption_format(paragraph)
    run = paragraph.add_run(text)
    set_font(run, east="宋体", size=10.5, ascii_font="Times New Roman")


def insert_paragraph_after(paragraph):
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    return Paragraph(new_p, paragraph._parent)


def para_has_image(paragraph):
    return bool(paragraph._p.findall(".//" + qn("a:blip")))


def find_paragraph(document, text):
    for paragraph in document.paragraphs:
        if paragraph.text.strip() == text:
            return paragraph
    raise ValueError(f"未找到段落: {text}")


def normalize_chapter5(document):
    start = find_paragraph(document, "第5章 系统实现")
    end = find_paragraph(document, "第6章 系统测试")
    in_range = False
    for paragraph in document.paragraphs:
        if paragraph is start:
            in_range = True
        if not in_range:
            continue
        if paragraph is end:
            break
        text = paragraph.text.strip()
        if not text or para_has_image(paragraph):
            continue
        if paragraph.style.name.startswith("标题"):
            continue
        if text in CAPTIONS:
            write_caption(paragraph, text)
        else:
            write_body(paragraph, text)


def main():
    shutil.copy2(SOURCE, OUTPUT)
    doc = Document(OUTPUT)

    anchors = {text: find_paragraph(doc, text) for text in REPLACEMENTS}

    for original_text, payload in REPLACEMENTS.items():
        paragraph = anchors[original_text]
        write_body(paragraph, payload["text"])
        current = paragraph
        for extra in payload.get("after", []):
            current = insert_paragraph_after(current)
            write_body(current, extra)

    for caption in CAPTIONS:
        paragraph = find_paragraph(doc, caption)
        write_caption(paragraph, caption)

    normalize_chapter5(doc)
    doc.save(OUTPUT)
    print(f"已生成: {OUTPUT}")


if __name__ == "__main__":
    main()
