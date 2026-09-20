const input = document.getElementById("input");
const send = document.getElementById("send");
const box = document.getElementById("messages");


function add(text, className) {

    const div = document.createElement("div");

    div.className = "bubble " + className;

    div.textContent = text;

    box.appendChild(div);

    box.scrollTop = box.scrollHeight;
}


async function go() {

    const text = input.value.trim();

    if (!text) {
        return;
    }


    // Mostrar mensaje del estudiante
    add(text, "me");

    input.value = "";

    send.disabled = true;

    // Cambiar temporalmente el texto del botón
    const originalButtonText = send.textContent;

    send.textContent = "Enviando...";


    // Mensaje temporal
    const loading = document.createElement("div");

    loading.className = "bubble bot";

    loading.textContent = "Estoy pensando...";

    loading.id = "loading-message";

    box.appendChild(loading);

    box.scrollTop = box.scrollHeight;


    // Tiempo máximo de espera
    const controller = new AbortController();

    const timeout = setTimeout(() => {
        controller.abort();
    }, 20000);


    try {

        const response = await fetch(
            "/api/chat",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    message: text
                }),

                signal: controller.signal
            }
        );


        clearTimeout(timeout);


        // Eliminar "Estoy pensando..."
        const loadingMessage =
            document.getElementById("loading-message");

        if (loadingMessage) {
            loadingMessage.remove();
        }


        // Revisar si el servidor respondió correctamente
        if (!response.ok) {

            throw new Error(
                "El servidor respondió con error " +
                response.status
            );
        }


        const data = await response.json();


        const reply =
            data.reply ||
            "No recibí una respuesta. Intenta nuevamente.";


        add(reply, "bot");


    } catch (error) {

        clearTimeout(timeout);


        // Eliminar mensaje de carga
        const loadingMessage =
            document.getElementById("loading-message");

        if (loadingMessage) {
            loadingMessage.remove();
        }


        console.error(
            "ERROR DEL CHAT:",
            error
        );


        if (error.name === "AbortError") {

            add(
                "La respuesta está tardando demasiado. " +
                "Intenta nuevamente en unos segundos.",
                "bot"
            );

        } else {

            add(
                "No pude conectarme con el asistente. " +
                "Comprueba tu conexión e intenta nuevamente.",
                "bot"
            );
        }


    } finally {

        // El botón siempre vuelve a funcionar
        send.disabled = false;

        send.textContent = originalButtonText;

        input.focus();
    }
}


send.onclick = go;


input.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Enter") {

            event.preventDefault();

            go();
        }
    }
);