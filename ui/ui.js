"use strict";

const field = (id) => document.getElementById(id);
const cases = {
  returns: "我刚收到桌灯，想退货，怎么操作？",
  shipping: "现货订单什么时候发货？在哪查物流？",
  exception: "桌灯烧坏划伤了桌面，你们能赔我多少？",
};
let confirmation = null;
let busy = false;

async function request(path, body) {
  const options = body === undefined ? undefined : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  };
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.error || "请求失败");
  return data;
}

function item(tag, value, parent) {
  const element = document.createElement(tag);
  element.textContent = value;
  parent.appendChild(element);
  return element;
}

async function tickets() {
  const data = await request("/api/tickets");
  const panel = field("ticket-list");
  panel.replaceChildren();
  if (!data.tickets.length) item("p", "当前没有人工工单", panel).className = "empty";
  for (const row of data.tickets) {
    const block = item("div", "", panel);
    block.className = "ticket";
    item("strong", `${row.id} · ${row.status}`, block);
    item("p", row.question, block);
  }
}

for (const button of document.querySelectorAll("[data-case]")) {
  button.addEventListener("click", () => {
    field("question").value = cases[button.dataset.case];
    field("question").focus();
  });
}

field("ask-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy) return;
  busy = true;
  const button = field("ask");
  button.disabled = true;
  confirmation = null;
  field("confirm-handoff").hidden = true;
  field("ticket-receipt").textContent = "";
  field("source").textContent = "";
  field("result").hidden = false;
  field("result").dataset.state = "loading";
  field("trace").textContent = "本地模型正在判断适用资料";
  field("answer").textContent = "";
  try {
    const data = await request("/api/ask", { question: field("question").value });
    field("result").dataset.state = data.status;
    field("trace").textContent = `模型候选 ${data.model_choice} · ${data.status === "answer" ? "引用依据" : "程序转人工"} · ${data.elapsed_ms} ms`;
    if (data.status === "answer") {
      field("answer").textContent = data.article.body;
      field("source").textContent = `依据 ${data.article.id} · ${data.article.title}`;
    } else {
      field("answer").textContent = data.message;
      confirmation = data.confirmation;
      field("confirm-handoff").hidden = false;
    }
  } catch (error) {
    field("trace").textContent = "本次未取得模型结果";
    field("answer").textContent = error.message;
  } finally {
    busy = false;
    button.disabled = false;
  }
});

field("confirm-handoff").addEventListener("click", async () => {
  if (!confirmation || busy) return;
  busy = true;
  const button = field("confirm-handoff");
  button.disabled = true;
  try {
    const data = await request("/api/handoff", { confirmation });
    field("ticket-receipt").textContent = `${data.reused ? "已存在" : "已写入"} ${data.id} · ${data.status}`;
    await tickets();
  } catch (error) {
    field("ticket-receipt").textContent = error.message;
  } finally {
    busy = false;
    button.disabled = false;
  }
});

request("/api/knowledge").then((data) => {
  for (const article of data.articles) {
    const li = item("li", "", field("knowledge-list"));
    item("strong", `${article.id} · ${article.title}`, li);
    item("small", article.scope, li);
  }
}).catch(() => item("li", "知识库加载失败", field("knowledge-list")));
tickets().catch(() => item("p", "本地工单读取失败", field("ticket-list")));
