const starterCode = `public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}`;

const editor = CodeMirror.fromTextArea(
    document.getElementById("code"),
    {
        mode: "text/x-java",
        theme: "material-darker",
        lineNumbers: true,
        indentUnit: 4,
        tabSize: 4
    }
);

editor.setValue(starterCode);

const stdin = document.getElementById("stdin");
const output = document.getElementById("output");
const runBtn = document.getElementById("runBtn");
const resetBtn = document.getElementById("resetBtn");

runBtn.addEventListener("click", async () => {
    const code = editor.getValue();

    if (!code.trim()) {
        output.textContent = "Please enter Java code.";
        return;
    }

    runBtn.disabled = true;
    runBtn.textContent = "⏳ Running...";
    output.textContent = "Compiling and running...";

    try {
        const response = await fetch("/api/run", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                code: code,
                stdin: stdin.value
            })
        });

        const data = await response.json();

        if (!response.ok) {
            output.textContent = data.error || "Something went wrong.";
            return;
        }

        let result = "";

        if (data.status) {
            result += `Status: ${data.status}\n\n`;
        }

        result += data.output || "No output.";

        if (data.time) {
            result += `\n\nTime: ${data.time}s`;
        }

        if (data.memory) {
            result += `\nMemory: ${data.memory} KB`;
        }

        output.textContent = result;

    } catch (error) {
        output.textContent =
            "Could not connect to the server.\n\n" + error.message;
    } finally {
        runBtn.disabled = false;
        runBtn.textContent = "▶ Run Java";
    }
});

resetBtn.addEventListener("click", () => {
    editor.setValue(starterCode);
    stdin.value = "";
    output.textContent = "Output will appear here...";
});

document.getElementById("clearInput").addEventListener("click", () => {
    stdin.value = "";
});

document.getElementById("clearOutput").addEventListener("click", () => {
    output.textContent = "Output will appear here...";
});
