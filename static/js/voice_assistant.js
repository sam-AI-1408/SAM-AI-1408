// =======================
// Sam AI – Flow Mode Voice Assistant
// =======================

let assistantActive = false;   // Whether assistant is "awake"
let listening = false;         // Mic on/off
let username = "Player";
let pendingAction = null;

// ===== Command Variations =====
const commandMap = {
  "tasks": ["task", "tasks", "tusk", "desk"],
  "academics": ["academic", "academics", "study", "studies", "education"],
  "quests": ["quest", "quests", "questz", "request"],
  "profile": ["profile", "account", "my profile"],
  "developers": ["developer", "developers", "team", "dev"],
  "logout": ["logout", "log out", "sign out"],

  "add task": ["add task", "create task", "new task"],
  "delete task": ["delete task", "remove task", "trash task"],
  "complete task": ["complete task", "finish task"],

  "add quest": ["add quest", "create quest"],
  "complete quest": ["complete quest", "finish quest"],

  "add session": ["add session", "create session"],
  "edit profile": ["edit profile", "update profile"],

  "time": ["time", "what time"],
  "date": ["date", "today"],
  "help": ["help", "commands", "what can you do"],
  "terminate": ["terminate", "stop", "close assistant"],
  "yes": ["yes", "yeah", "ok"],
  "no": ["no", "nope", "cancel"]
};

// ===== Normalize Command =====
function normalizeCommand(input) {
  input = input.toLowerCase().trim();
  for (const [main, variants] of Object.entries(commandMap)) {
    for (let v of variants) {
      if (input.includes(v)) return main;
    }
  }
  // Natural language fallback
  if (/open.*task/.test(input)) return "tasks";
  if (/open.*quest/.test(input)) return "quests";
  if (/open.*academic/.test(input) || /study/.test(input)) return "academics";
  if (/open.*profile/.test(input) || /account/.test(input)) return "profile";
  if (/log.?out/.test(input)) return "logout";
  return null;
}

// ===== Feedback + Voice =====
function showFeedback(text) {
  feedback.innerText = text;
  feedback.style.display = "block";
  speakAI(text);
}

function speakAI(text) {
  const synth = window.speechSynthesis;
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1; utter.pitch = 1;
  utter.voice = synth.getVoices().find(v => v.name.toLowerCase().includes("female")) || synth.getVoices()[0];
  synth.speak(utter);
}

// ===== UI Elements =====
const micBtn = document.createElement("button");
micBtn.id = "sam-voice-btn";
micBtn.innerHTML = "🎤";
Object.assign(micBtn.style, {
  position: "fixed", bottom: "25px", right: "25px",
  width: "60px", height: "60px", borderRadius: "50%",
  border: "none", backgroundColor: "#00d0ff", color: "#050615",
  fontSize: "28px", cursor: "pointer", boxShadow: "0 4px 15px rgba(0,0,0,0.3)",
  zIndex: "9999"
});
document.body.appendChild(micBtn);

const feedback = document.createElement("div");
feedback.id = "sam-voice-feedback";
Object.assign(feedback.style, {
  position: "fixed", bottom: "95px", right: "25px",
  background: "#0f1630", color: "#00d0ff", padding: "10px 16px",
  borderRadius: "12px", boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
  fontFamily: "Arial, sans-serif", fontSize: "14px",
  maxWidth: "350px", display: "none", whiteSpace: "pre-wrap"
});
document.body.appendChild(feedback);

// ===== Command Execution =====
function handleAction(rawCommand) {
  const normalized = normalizeCommand(rawCommand);

  // Wake word
  if (!assistantActive && (rawCommand.includes("arise") || rawCommand.includes("hey sam"))) {
    assistantActive = true;
    showFeedback(`Hello ${username}, I'm ready to help you.`);
    return;
  }

  // If not active, ignore everything except wake word
  if (!assistantActive) return;

  switch (normalized) {
    case "tasks": window.location.href = "/tasks"; showFeedback("Opening tasks."); break;
    case "academics": window.location.href = "/academics"; showFeedback("Opening academics."); break;
    case "quests": window.location.href = "/quests"; showFeedback("Opening quests."); break;
    case "profile": window.location.href = "/profile"; showFeedback("Opening profile."); break;
    case "developers": window.location.href = "/developers"; showFeedback("Opening developers page."); break;
    case "logout": pendingAction = () => { window.location.href = "/logout"; }; showFeedback("Do you want to log out? Say Yes or No."); break;

    case "add task": document.querySelector("#add-task-btn")?.click(); showFeedback("Adding a task."); break;
    case "delete task": pendingAction = () => { showFeedback("Task deleted."); }; showFeedback("Do you want to delete this task?"); break;
    case "complete task": showFeedback("Task marked completed."); break;

    case "add quest": document.querySelector("#add-quest-btn")?.click(); showFeedback("Adding a quest."); break;
    case "complete quest": showFeedback("Quest completed."); break;

    case "add session": document.querySelector("#add-session-btn")?.click(); showFeedback("Adding a new session."); break;
    case "edit profile": window.location.href = "/profile/edit"; showFeedback("Opening profile editor."); break;

    case "time": showFeedback(`The time is ${new Date().toLocaleTimeString()}.`); break;
    case "date": showFeedback(`Today is ${new Date().toDateString()}.`); break;

    case "help":
      showFeedback("Commands: tasks, academics, quests, profile, developers, add task, delete task, complete task, add session, edit profile, logout, time, date, terminate.");
      break;

    case "yes":
      if (pendingAction) { pendingAction(); pendingAction = null; }
      break;
    case "no":
      if (pendingAction) { showFeedback("Action cancelled."); pendingAction = null; }
      break;

    case "terminate":
      assistantActive = false;
      showFeedback("Assistant deactivated. Say 'Arise' again to reactivate.");
      break;

    default:
      showFeedback("Sorry, I didn’t catch that. Say 'help' for a list of commands.");
  }
}

// ===== Speech Recognition =====
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang = "en-US";
recognition.interimResults = false;
recognition.continuous = true;

// Restart listening automatically
recognition.onend = () => { if (listening) recognition.start(); };

recognition.onresult = (event) => {
  const command = event.results[event.results.length - 1][0].transcript;
  console.log("Heard:", command);
  handleAction(command);
};

recognition.onerror = (event) => {
  console.error("Recognition error:", event.error);
  showFeedback("Error: " + event.error);
};

// ===== Mic Button Control =====
micBtn.addEventListener("click", () => {
  if (!listening) {
    recognition.start();
    listening = true;
    showFeedback("🎤 Mic activated. Say 'Arise' to start the assistant.");
  } else {
    recognition.stop();
    listening = false;
    assistantActive = false; // reset assistant when mic is turned off
    showFeedback("Mic turned off.");
  }
});
