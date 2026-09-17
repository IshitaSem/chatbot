const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

function timeNow() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function addBubble(text, sender, options = null) {
    const row = document.createElement("div");
    row.className = `bubble-row ${sender}`;

    const bubble = document.createElement("div");
    bubble.className = `bubble ${sender}`;

    const name = document.createElement("div");
    name.className = "bubble-name";
    name.textContent = sender === "bot" ? "Cafe Delight" : "You";

    const msg = document.createElement("div");
    msg.textContent = text;

    bubble.appendChild(name);
    bubble.appendChild(msg);

    if (options && options.length > 0) {
        const btnContainer = document.createElement("div");
        btnContainer.className = "option-buttons";
        options.forEach(opt => {
            const btn = document.createElement("button");
            btn.className = "option-btn";
            btn.textContent = opt.label;

            const lowVal = (opt.value || "").toLowerCase();
            const lowLabel = (opt.label || "").toLowerCase();

            if (lowVal === "confirm" || lowLabel.includes("confirm")) {
                btn.classList.add("btn-confirm");
            } else if (lowVal === "cancel" || lowLabel.includes("cancel")) {
                btn.classList.add("btn-cancel");
            } else {
                btn.classList.add("btn-general");
            }

            btn.onclick = () => {
                const allBtns = btnContainer.querySelectorAll("button");
                allBtns.forEach(b => {
                    b.disabled = true;
                });
                sendToChat(opt.value);
            };
            btnContainer.appendChild(btn);
        });
        bubble.appendChild(btnContainer);
    }

    const time = document.createElement("div");
    time.className = "bubble-time";
    time.textContent = timeNow();
    bubble.appendChild(time);

    row.appendChild(bubble);
    chatWindow.appendChild(row);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function updateCartSidebar(cart) {
    const linesDiv = document.getElementById("cart-lines");
    const itemCount = document.getElementById("item-count");
    const totalAmount = document.getElementById("total-amount");

    if (!cart.lines.length) {
        linesDiv.innerHTML = "Your cart is empty.<br><br>Add something delicious<br>to get started.";
        itemCount.textContent = "0 items";
        totalAmount.textContent = "Rs. 0";
        return;
    }

    let text = "";
    cart.lines.forEach(l => {
        text += `${l.quantity} x ${l.item}\nRs. ${l.amount}\n\n`;
    });
    linesDiv.textContent = text.trim();
    itemCount.textContent = `${cart.total_items} items`;
    totalAmount.textContent = `Rs. ${cart.total}`;
}

let appState = null;

async function sendToChat(text, showUserBubble = true) {
    if (showUserBubble) addBubble(text, "user");

    const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, state: appState })
    });
    const data = await res.json();
    if (data.state) appState = data.state;
    if (data.message) addBubble(data.message, "bot", data.options);
    updateCartSidebar(data.cart);
}

sendBtn.onclick = () => {
    const text = userInput.value.trim();
    if (!text) return;
    userInput.value = "";
    sendToChat(text);
};

userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendBtn.click();
});

document.getElementById("btn-menu").onclick = () => sendToChat("show menu");
document.getElementById("btn-order").onclick = () => sendToChat("I want to order");

document.getElementById("btn-cart").onclick = async () => {
    const res = await fetch("/api/cart/view", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: appState })
    });
    const data = await res.json();
    if (data.state) appState = data.state;
    addBubble(data.message, "bot");
    updateCartSidebar(data.cart);
};

document.getElementById("btn-clear").onclick = async () => {
    if (!confirm("Are you sure you want to clear your current order?")) return;
    const res = await fetch("/api/cart/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: appState })
    });
    const data = await res.json();
    if (data.state) appState = data.state;
    addBubble(data.message, "bot");
    updateCartSidebar(data.cart);
};

window.onload = () => {
    addBubble(
        "Welcome to Cafe Delight!\n\n" +
        "I am your personal ordering assistant. I can help you explore our menu, check prices, " +
        "describe dishes and place your order.\n\n" +
        "What would you like to have today?",
        "bot"
    );
};