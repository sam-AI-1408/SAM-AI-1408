<<<<<<< HEAD
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
=======
// =======================
// Sam AI Voice Assistant (Offline Female Voice Only)
// =======================

let assistantActive = false;
let username = window.username || "Player";

// ================= UI Elements =================
const micBtn = document.createElement("button");
micBtn.id = "sam-voice-btn";
micBtn.innerHTML = "🎤";
Object.assign(micBtn.style, {
  position: "fixed",
  bottom: "25px",
  right: "25px",
  width: "60px",
  height: "60px",
  borderRadius: "50%",
  border: "none",
  backgroundColor: "#00d0ff",
  color: "#050615",
  fontSize: "28px",
  cursor: "pointer",
  boxShadow: "0 4px 15px rgba(0,0,0,0.3)",
  zIndex: "9999",
});
document.body.appendChild(micBtn);

const feedback = document.createElement("div");
feedback.id = "sam-voice-feedback";
Object.assign(feedback.style, {
  position: "fixed",
  bottom: "95px",
  right: "25px",
  background: "#0f1630",
  color: "#00d0ff",
  padding: "10px 16px",
  borderRadius: "12px",
  boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
  fontFamily: "Arial, sans-serif",
  fontSize: "14px",
  maxWidth: "350px",
  display: "none",
  whiteSpace: "pre-wrap"
});
document.body.appendChild(feedback);

// ================= Speak Function =================
function selectFemaleVoice() {
  let voices = speechSynthesis.getVoices();
  if (!voices.length) {
    setTimeout(selectFemaleVoice, 100);
    return null;
  }
  return voices.find(v => v.lang.startsWith("en") && v.name.toLowerCase().includes("female")) || voices[0];
}

function speak(text) {
  const utter = new SpeechSynthesisUtterance(text);
  utter.voice = selectFemaleVoice();
  utter.rate = 1;
  utter.pitch = 1.2;
  // Add slight delay for natural effect
  setTimeout(() => speechSynthesis.speak(utter), 500);
}

// ================= UI Feedback =================
const history = [];
function showFeedback(text) {
  history.unshift(text);
  feedback.innerText = history.slice(0, 5).join("\n");
  feedback.style.display = "block";
}

// ================= Command Processor =================
function processCommand(command) {
  command = command.toLowerCase();
  let response = "";

  if (!assistantActive) {
    if (command.includes("arise")) {
      assistantActive = true;
      response = `Hi ${username}, how was your day?`;
    } else {
      response = `Say "Arise" to activate me.`;
    }
    showFeedback(response);
    speak(response);
    return;
  }

  // ================= Commands =================
  if (command.includes("hello") || command.includes("hi")) {
    response = `Hello ${username}! How can I help you today?`;
  } else if (command.includes("how are you")) {
    response = "I'm great, ready to assist you!";
  } else if (command.includes("good") || command.includes("nice")) {
    response = `Glad to hear that, ${username}.`;
  } else if (command.includes("arise")) {
    response = "I am already awake!";
  } else if (command.includes("terminate") || command.includes("close")) {
    assistantActive = false;
    response = "Voice assistant closed. Say 'Arise' to reactivate me.";
  } else if (command.includes("tasks")) {
    response = "Opening your tasks dashboard.";
    window.location.href = "/tasks";
  } else if (command.includes("add task")) {
    response = "Please enter your task on the dashboard to add it.";
  } else if (command.includes("complete task")) {
    response = "Mark the task completed on the dashboard.";
  } else if (command.includes("delete task")) {
    response = "Select the task you want to delete on the dashboard.";
  } else if (command.includes("academics")) {
    response = "Opening your academics dashboard.";
    window.location.href = "/academics";
  } else if (command.includes("study log")) {
    response = "You can add a study log via the academics dashboard.";
  } else if (command.includes("quests")) {
    response = "Opening your quests dashboard.";
    window.location.href = "/quests";
  } else if (command.includes("daily quest")) {
    response = "Check your daily quests in the quests dashboard.";
  } else if (command.includes("weekly quest")) {
    response = "Check your weekly quests in the quests dashboard.";
  } else if (command.includes("monthly quest")) {
    response = "Check your monthly quests in the quests dashboard.";
  } else if (command.includes("profile")) {
    response = "Opening your profile page.";
    window.location.href = "/profile";
  } else if (command.includes("edit profile")) {
    response = "You can edit your profile from the profile page.";
    window.location.href = "/edit-profile";
  } else if (command.includes("points")) {
    response = `You currently have ${window.userPoints || 0} points.`;
  } else if (command.includes("rank")) {
    response = `Your rank is ${window.userRank || "Bronze"}.`;
  } else if (command.includes("level")) {
    response = `Your level is ${window.userLevel || 1}.`;
  } else if (command.includes("health")) {
    response = `Your health is ${window.userHealth || 50}.`;
  } else if (command.includes("strength")) {
    response = `Your strength is ${window.userStrength || 50}.`;
  } else if (command.includes("finance")) {
    response = `Your finance score is ${window.userFinance || 50}.`;
  } else if (command.includes("wisdom")) {
    response = `Your wisdom score is ${window.userWisdom || 50}.`;
  } else if (command.includes("growth")) {
    response = `Your growth score is ${window.userGrowth || 50}.`;
  } else if (command.includes("motivation")) {
    response = "Keep pushing forward! Every day is a new level to conquer!";
  } else if (command.includes("developers")) {
    response = "Opening the developers page.";
    window.location.href = "/developers";
  } else if (command.includes("logout")) {
    response = "Logging out.";
    fetch("/logout", { method: "POST" }).then(() => window.location.href = "/login");
  } else if (command.includes("help")) {
    response = "You can say commands like: tasks, academics, quests, profile, points, rank, level, strength, wisdom, logout.";
  } else if (command.includes("thank you") || command.includes("thanks")) {
    response = "You're welcome!";
  } else if (command.includes("joke")) {
    const jokes = [
      "Why did the computer go to the doctor? Because it caught a virus!",
      "Why do programmers prefer dark mode? Because light attracts bugs!",
      "Why did the developer go broke? Because he used up all his cache!"
    ];
    response = jokes[Math.floor(Math.random() * jokes.length)];
  } else if (command.includes("time")) {
    const now = new Date();
    response = `The current time is ${now.getHours()}:${now.getMinutes()}`;
  } else if (command.includes("date")) {
    const now = new Date();
    response = `Today's date is ${now.toDateString()}`;
  } else if (command.includes("weather")) {
    response = "Check your local weather dashboard for current weather info.";
  } else {
    response = "Sorry, I didn’t understand that command.";
  }

  showFeedback(response);
  speak(response);
}

// ================= Speech Recognition Setup =================
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang = "en-US";
recognition.interimResults = false;
recognition.maxAlternatives = 1;
recognition.continuous = true;

recognition.onresult = (event) => {
  const command = event.results[event.results.length - 1][0].transcript;
  console.log("Heard command:", command);
  processCommand(command);
};

recognition.onerror = (event) => {
  console.error("Recognition error:", event.error);
  showFeedback("Error: " + event.error);
};

recognition.onspeechstart = () => {
  showFeedback("Listening...");
};
recognition.onspeechend = () => {
  showFeedback(assistantActive ? "Waiting for your next command..." : 'Say "Arise" to activate me.');
};
recognition.onend = () => recognition.start();
recognition.start();

// ================= Optional Mic Button Feedback =================
micBtn.addEventListener("click", () => {
  showFeedback(assistantActive ? "Listening..." : 'Say "Arise" to activate me.');
});
>>>>>>> 9cec5c74b6e8c211f34090f2898531cd55da02ab
