// ======================
// Sam AI – Advanced Voice Assistant
// ======================

let assistantActive = false;
let listening = false;
let muteTTS = false;
let username = localStorage.getItem("sam_username") || "Player";
let pendingAction = null;

// ===== Game Navigation Links =====
const gameCommands = {
  "coin game": "/coin",
  "dice game": "/dice",
  "market game": "/market",
  "save or spend": "/save",
  "money quiz": "/money",
  "budget builder": "/build"
};

// ===== Command Map =====
const commandMap = {
  "roll dice": ["roll dice"],
  "buy item": ["buy item"],
  "sell item": ["sell item"],
  "save coins": ["save coins","deposit coins"],
  "spend coins": ["spend coins","use coins"],
  "collect coin": ["collect coin","pick coin"],
  "current score": ["score","my score"],
  "my coins": ["coins","coin balance","bank"],
  "restart game": ["restart game","new game"],
  "game hint": ["hint","help me","advice"],
  "pause listening": ["pause listening"],
  "resume listening": ["resume listening"],
  "mute assistant": ["mute","mute assistant"],
  "unmute assistant": ["unmute","unmute assistant"],
  "tasks": ["task","tasks","tusk","desk"],
  "academics": ["academic","study","studies"],
  "quests": ["quest","quests","request"],
  "profile": ["profile","account","my profile"],
  "developers": ["developer","developers","team","dev"],
  "logout": ["logout","log out","sign out"],
  "help": ["help","commands","what can you do"],
  "terminate": ["terminate","stop","close assistant"],
  "yes": ["yes","yeah","ok"],
  "no": ["no","nope","cancel"]
};

// ===== Normalize Command =====
function normalizeCommand(input){
  input = input.toLowerCase().trim();
  for(const [main, variants] of Object.entries(commandMap)){
    for(let v of variants){
      if(input.includes(v)) return main;
    }
  }
  return null;
}

// ===== Feedback + TTS =====
const feedback = document.createElement("div");
feedback.id="sam-voice-feedback";
Object.assign(feedback.style,{
  position:"fixed", bottom:"95px", right:"25px",
  background:"#0f1630", color:"#00d0ff", padding:"10px 16px",
  borderRadius:"12px", boxShadow:"0 4px 20px rgba(0,0,0,0.5)",
  fontFamily:"Arial,sans-serif", fontSize:"14px",
  maxWidth:"350px", display:"none", whiteSpace:"pre-wrap", zIndex:"9999"
});
document.body.appendChild(feedback);

function showFeedback(text,type="info"){
  feedback.innerText=text;
  feedback.style.display="block";
  feedback.style.backgroundColor = type==="success"? "#004d00" : type==="warn"? "#662200" : "#0f1630";
  if(!muteTTS) speakAI(text);
  setTimeout(()=>feedback.style.display="none",5000);
}

function speakAI(text){
  const synth = window.speechSynthesis;
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate=1; utter.pitch=1;
  utter.voice = synth.getVoices().find(v=>v.name.toLowerCase().includes("female"))||synth.getVoices()[0];
  synth.speak(utter);
}

// ===== Mic Button =====
const micBtn = document.createElement("button");
micBtn.id="sam-voice-btn";
micBtn.innerHTML="🎤";
Object.assign(micBtn.style,{
  position:"fixed", bottom:"25px", right:"25px",
  width:"60px", height:"60px", borderRadius:"50%",
  border:"none", backgroundColor:"#00d0ff", color:"#050615",
  fontSize:"28px", cursor:"pointer", boxShadow:"0 4px 15px rgba(0,0,0,0.3)",
  zIndex:"9999"
});
document.body.appendChild(micBtn);

// ===== Game Hint System =====
function provideHint(){
  let hint = "Try to earn more coins!";
  // Coin Collector
  if(typeof window.score!=="undefined"){
    if(window.score<50) hint="Click coins fast to increase your score!";
    else hint="Great job! Keep collecting coins!";
  }
  // Market Game
  if(typeof window.coins!=="undefined" && typeof window.items!=="undefined"){
    if(window.items===0) hint="Buy items low, sell high!";
    else hint="Consider selling some items for profit!";
  }
  // Save/Spend
  if(typeof window.bank!=="undefined" && typeof window.budget!=="undefined"){
    if(window.budget>0) hint="You can save this budget to increase your bank!";
    else hint="Wait for next budget!";
  }
  // Money Quiz
  if(typeof window.current!=="undefined" && typeof window.score!=="undefined"){
    hint="Answer carefully to earn more points!";
  }
  showFeedback("💡 Hint: "+hint,"success");
}

// ===== Command Execution =====
function handleAction(rawCommand){
  const normalized = normalizeCommand(rawCommand);

  // Wake Word
  if(!assistantActive && (rawCommand.includes("arise") || rawCommand.includes("hey sam"))){
    assistantActive=true;
    showFeedback(`Hello ${username}! I'm ready to assist you. Say 'help' for commands.`,"success");
    return;
  }
  if(!assistantActive) return;

  switch(normalized){
    // Mini-game actions
    case "roll dice": window.rollDice?.(); showFeedback("Rolling the dice!","success"); break;
    case "buy item": window.buyItem?.(); showFeedback("Buying item!","success"); break;
    case "sell item": window.sellItem?.(); showFeedback("Selling item!","success"); break;
    case "save coins": window.saveBudget?.(); showFeedback("Saving coins!","success"); break;
    case "spend coins": window.spendBudget?.(); showFeedback("Spending coins!","warn"); break;
    case "collect coin": window.collectCoin?.(); showFeedback("Collecting coin!","success"); break;
    case "current score": showFeedback(`Your current score is ${window.score||0}`); break;
    case "my coins": showFeedback(`You have ${window.coins||window.bank||0} coins.`); break;
    case "restart game": window.resetGame?.(); showFeedback("Game restarted!","success"); break;
    case "game hint": provideHint(); break;

    // System controls
    case "pause listening": listening=false; recognition.stop(); showFeedback("Listening paused.","warn"); break;
    case "resume listening": listening=true; recognition.start(); showFeedback("Listening resumed.","success"); break;
    case "mute assistant": muteTTS=true; showFeedback("Assistant muted.","warn"); break;
    case "unmute assistant": muteTTS=false; showFeedback("Assistant unmuted.","success"); break;

    // Navigation / pages
    case "tasks": window.location.href="/tasks"; showFeedback("Opening tasks.","success"); break;
    case "academics": window.location.href="/academics"; showFeedback("Opening academics.","success"); break;
    case "quests": window.location.href="/quests"; showFeedback("Opening quests.","success"); break;
    case "profile": window.location.href="/profile"; showFeedback("Opening profile.","success"); break;
    case "developers": window.location.href="/developers"; showFeedback("Opening developers page.","success"); break;
    case "logout": pendingAction=()=>window.location.href="/logout"; showFeedback("Do you want to log out? Say Yes or No.","warn"); break;

    case "help": showFeedback("Commands: roll dice, buy item, sell item, save coins, spend coins, collect coin, current score, my coins, restart game, hint, pause/resume listening, mute/unmute, mini-games, tasks, academics, quests, profile, developers, logout"); break;
    case "terminate": assistantActive=false; showFeedback("Assistant terminated. Say 'Arise' to activate again.","warn"); break;
    case "yes": if(pendingAction){pendingAction(); pendingAction=null;} break;
    case "no": if(pendingAction){showFeedback("Action cancelled."); pendingAction=null;} break;

    default:
      // Check mini-game navigation
      for(let g in gameCommands){
        if(rawCommand.includes(g)){
          window.location.href = gameCommands[g];
          showFeedback(`Opening ${g}`,"success");
          return;
        }
      }
      showFeedback("Sorry, I didn’t catch that. Say 'help' for commands.","warn");
  }
}

// ===== Speech Recognition =====
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang="en-US";
recognition.interimResults=false;
recognition.continuous=true;

recognition.onend=()=>{if(listening) recognition.start();};
recognition.onresult=(event)=>{
  const command=event.results[event.results.length-1][0].transcript;
  console.log("Heard:",command);
  handleAction(command);
};
recognition.onerror=(event)=>{ console.error("Recognition error:",event.error); showFeedback("Error: "+event.error,"warn"); };

// ===== Mic Button =====
micBtn.addEventListener("click",()=>{
  if(!listening){
    recognition.start();
    listening=true;
    assistantActive=false;
    showFeedback("🎤 Mic activated. Say 'Arise' to start the assistant.");
  } else {
    recognition.stop();
    listening=false;
    assistantActive=false;
    showFeedback("Mic turned off.");
  }
});