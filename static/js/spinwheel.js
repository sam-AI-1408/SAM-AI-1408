// ============================
// Spin Wheel – SAM AI-1408
// ============================

const options = [
  { name: "Push-ups 💪", task: "Do 10 Push-ups" },
  { name: "Squats 🦵", task: "Do 15 Squats" },
  { name: "Plank 🧘", task: "Hold Plank for 20s" },
  { name: "Jumping Jacks 🏃", task: "Do 20 Jumping Jacks" }
];

const canvas = document.getElementById("wheelCanvas");
const ctx = canvas.getContext("2d");
const spinBtn = document.getElementById("spinBtn");
const resultBox = document.getElementById("resultBox");
const doneBtn = document.getElementById("doneBtn");

let startAngle = 0;
const arc = (2 * Math.PI) / options.length;
let spinTimeout = null;
let spinAngleStart = 0;
let spinTime = 0;
let spinTimeTotal = 0;
let selectedOption = null;

// 🎡 Draw the wheel
function drawWheel() {
  ctx.clearRect(0, 0, 400, 400);

  for (let i = 0; i < options.length; i++) {
    const angle = startAngle + i * arc;
    ctx.beginPath();
    ctx.fillStyle = i % 2 === 0 ? "#ff6b6b" : "#4dabf7";
    ctx.moveTo(200, 200);
    ctx.arc(200, 200, 200, angle, angle + arc);
    ctx.lineTo(200, 200);
    ctx.fill();

    // Text
    ctx.save();
    ctx.fillStyle = "#fff";
    ctx.translate(200, 200);
    ctx.rotate(angle + arc / 2);
    ctx.font = "16px Segoe UI";
    ctx.textAlign = "right";
    ctx.fillText(options[i].name, 190, 5);
    ctx.restore();
  }

  // Pointer
  ctx.fillStyle = "#fff";
  ctx.beginPath();
  ctx.moveTo(190, 0);
  ctx.lineTo(210, 0);
  ctx.lineTo(200, 30);
  ctx.fill();
}

// 🎡 Spin logic
function rotateWheel() {
  spinAngleStart = Math.random() * 10 + 10;
  spinTime = 0;
  spinTimeTotal = Math.random() * 3000 + 4000;
  rotateAnimation();
}

function rotateAnimation() {
  spinTime += 30;
  if (spinTime >= spinTimeTotal) {
    stopRotateWheel();
    return;
  }
  const spinAngle = spinAngleStart - easeOut(spinTime, 0, spinAngleStart, spinTimeTotal);
  startAngle += (spinAngle * Math.PI) / 180;
  drawWheel();
  spinTimeout = setTimeout(rotateAnimation, 30);
}

function stopRotateWheel() {
  clearTimeout(spinTimeout);
  const degrees = (startAngle * 180 / Math.PI + 90) % 360;
  const index = Math.floor((360 - degrees) / (360 / options.length)) % options.length;
  selectedOption = options[index];

  resultBox.textContent = "🎯 Challenge: " + selectedOption.task;
  doneBtn.style.display = "inline-block"; // show done button
}

// easing
function easeOut(t, b, c, d) {
  const ts = (t /= d) * t;
  const tc = ts * t;
  return b + c * (tc + -3 * ts + 3 * t);
}

// 🎯 Done button → send XP and redirect
doneBtn.addEventListener("click", async () => {
  if (!selectedOption) return;

  try {
    const response = await fetch("/spinwheel/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ exercise: selectedOption.name })
    });

    const data = await response.json();

    if (data.success) {
      resultBox.textContent = `✅ Completed! You earned ${data.xp} XP (${selectedOption.name})`;

      // hide button after click
      doneBtn.style.display = "none";

      // Redirect to tasks page after 1.5s
      setTimeout(() => {
        window.location.href = "/tasks"; // your Flask route
      }, 1500);

    } else {
      resultBox.textContent = "⚠️ Error: " + (data.message || "Try again");
    }

  } catch (err) {
    console.error(err);
    resultBox.textContent = "⚠️ Could not connect to server.";
  }
});

// Init
drawWheel();
spinBtn.addEventListener("click", rotateWheel);
