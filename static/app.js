const problemForm = document.getElementById("problem-form");
const problemSelect = document.getElementById("problem-select");
const runBtn = document.getElementById("run-btn");
const resultBox = document.getElementById("result");

async function loadProblems() {
  const res = await fetch("/api/problems");
  const problems = await res.json();
  problemSelect.innerHTML = "";
  for (const p of problems) {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = `#${p.id} ${p.title}`;
    problemSelect.appendChild(opt);
  }
}

problemForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const lines = document
    .getElementById("cases")
    .value.split("\n")
    .map((x) => x.trim())
    .filter(Boolean);
  const testcases = lines.map((line) => {
    const [input, output] = line.split("=>").map((x) => x.trim());
    return { input: input || "", output: output || "" };
  });

  const body = {
    title: document.getElementById("title").value,
    description: document.getElementById("description").value,
    time_limit: Number(document.getElementById("time_limit").value || 1),
    testcases,
  };

  const res = await fetch("/api/problems", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json();
    alert(err.error || "保存失败");
    return;
  }

  problemForm.reset();
  await loadProblems();
});

runBtn.addEventListener("click", async () => {
  const problemId = Number(problemSelect.value);
  if (!problemId) {
    alert("请先创建并选择题目");
    return;
  }

  const code = document.getElementById("code").value;
  const res = await fetch("/api/judge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ problem_id: problemId, code }),
  });
  const data = await res.json();
  resultBox.textContent = JSON.stringify(data, null, 2);
});

loadProblems();
