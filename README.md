# 灯屿客服实验台

这个 Windows 教学项目用本地 **Qwen3-1.7B** 判断顾客的问题适用哪条资料，用 Python 回传对应知识库原文，并在顾客确认后把转人工申请写入 SQLite。店铺、政策和顾客问题均为虚构。网页内的“待人工处理”指本机队列。

教程与示例应用由 **西楚极客**制作。Qwen3 是 Qwen 团队发布的模型，llama.cpp 由 ggml-org 项目及其贡献者维护。启动器从上游下载固定版本的运行器和模型，核对 SHA-256 后才解包。应用与模型在运行时通过本机地址通信。

## Windows x64 安装

1. 安装 [Python 3.12 或更新版](https://www.python.org/downloads/windows/)，安装时勾选 `Add python.exe to PATH`。在终端运行 `python --version` 或 `py -3 --version` 确认版本。准备期间需访问 GitHub 和 Hugging Face，预留约 4 GB 磁盘空间，模型下载约 1.83 GB。示例使用 CPU。
2. 将 ZIP 完整解压到可写目录。打开含 `start.cmd`、`prepare-runtime.cmd` 和 `knowledge.json` 的那一层。
3. 双击 **`prepare-runtime.cmd`**。看到“运行器与模型已准备完成”后关闭该窗口。若网络受限，可分别从下面的固定版本下载同名官方文件，放在一个目录，运行 `python -X utf8 runtime.py prepare --from-cache "C:\你的下载目录"`。已经准备好的同版本文件可以复用。
4. 双击 **`start.cmd`**。看到“客服已就绪”后访问 [本机客服实验台](http://127.0.0.1:18768/)。如果浏览器未自动打开，手动粘贴该地址。结束练习时在启动窗口按 Ctrl+C。

## 跟视频验收

| 操作 | 看到什么 |
| --- | --- |
| 点「普通退货」填入问题，再点「发送问题」 | 模型候选 `RETURN-01`，回复引用演示政策原文。对照右侧同编号资料。 |
| 点「查看发货」再发送 | 引用 `SHIP-02`，说明演示店的发货时间和查询入口。 |
| 点「损坏与赔偿」再发送 | 程序转人工，右侧工单仍为空。模型候选可能随模型版本、运行环境或问题文字变化。 |
| 点「确认转人工」 | 右侧出现本地工单，例如 `CS-0001`。对同一次确认重复点击只返回同一编号。 |
| 刷新页面，或停止后重新启动 | 使用同一数据库时，队列仍显示此前的工单。 |

修改 `knowledge.json` 中某条 `body`，重启后再提相同问题，观察引用文字的变化。添加资料时先给唯一 `id`、`title`、`scope`、`keywords`、`body`，再用命中和未命中的问题分别测试。应用中的关键词校验能辅助拦截误选，超出可靠覆盖的问题仍需要人工处理。

## 文件与排错

- `knowledge.json` 保存演示知识。`server.py` 负责模型选择、规则校验和入库。`ui/` 是本机网页。`runtime.py` 管理下载、校验和运行模型。
- 第一次启动会在 `data/support.sqlite3` 创建本机数据库。需要空队列重新练习，可以运行 `python -X utf8 runtime.py start --db data/rehearsal.sqlite3`，原数据库文件保留。
- 网页加载不到模型结果时，看启动窗口和 `runtime/model.log`。两个服务分别监听 `127.0.0.1:18767` 和 `127.0.0.1:18768`。端口已占用时先停止另一个同样的演示实例。
- `准备失败` 时检查错误所指文件、网络与剩余空间。SHA-256 不符的文件移出后再尝试。运行器或模型仍可从下方官方固定版本重新获取。
- 这个学习项目使用本机、单人和虚构数据。真实业务需要登录、权限、隐私和人工队列接入。

## 固定上游版本

- [llama.cpp b12588 Windows x64 CPU ZIP](https://github.com/ggml-org/llama.cpp/releases/download/b12588/llama-b12588-bin-win-cpu-x64.zip)，约 25 MB。运行器原项目使用 MIT 许可。
- [Qwen3-1.7B Q8_0 GGUF](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/blob/90862c4b9d2787eaed51d12237eafdfe7c5f6077/Qwen3-1.7B-Q8_0.gguf)，Apache-2.0。
- [Python](https://www.python.org/downloads/windows/) 提供 Python 运行环境；示例应用本身只使用标准库。
