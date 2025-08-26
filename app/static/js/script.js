let mediaRecorder;
let audioChunks = [];
let audioContext;
let analyser;
let dataArray;

const statusText = document.getElementById('statusText');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const micBtn = document.getElementById('micBtn');

let stream;
let recordingStartTime;

startBtn.addEventListener('click', async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createMediaStreamSource(stream);
        analyser = audioContext.createAnalyser();
        source.connect(analyser);
        analyser.fftSize = 256;
        const bufferLength = analyser.frequencyBinCount;
        dataArray = new Uint8Array(bufferLength);

        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                audioChunks.push(e.data);
                console.log('Chunk size:', e.data.size, 'bytes');
            }
        };
        mediaRecorder.start();
        recordingStartTime = Date.now();
        statusText.innerText = "Recording... (click Stop when ready)";
        stopBtn.disabled = false;

        function animateMic() {
            if (!mediaRecorder || mediaRecorder.state === "inactive") {
                micBtn.style.transform = "scale(1)";
                return;
            }
            analyser.getByteTimeDomainData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
                let value = dataArray[i] - 128;
                sum += value * value;
            }
            let volume = Math.sqrt(sum / dataArray.length) / 128;
            micBtn.style.transform = `scale(${1 + volume})`;
            requestAnimationFrame(animateMic);
        }
        animateMic();
    } catch (error) {
        console.error('Error starting recording:', error);
        statusText.innerText = "Error: Microphone access denied or unavailable";
    }
});

stopBtn.addEventListener('click', async () => {
    if (!mediaRecorder || mediaRecorder.state === "inactive") return;

    mediaRecorder.onstop = async () => {
        const duration = (Date.now() - recordingStartTime) / 1000;
        console.log('Recording duration:', duration, 'seconds');
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        console.log('Final blob size:', audioBlob.size, 'bytes');
        if (audioBlob.size < 500) { 
            statusText.innerText = "Error: Recording too short or empty";
            console.error('Recording too short or empty');
            return;
        }

        statusText.innerText = "Processing audio...";

        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');

        try {
            const response = await fetch('/process_audio', {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                throw new Error(`HTTP error: ${response.status}`);
            }
            const result = await response.json();
            console.log('Server response:', result);
            if (!result.transcription) {
                statusText.innerText = "Transcription: (empty, possibly silent or unclear audio)";
                console.warn('Empty transcription received');
            } else {
                statusText.innerText = `Transcription: ${result.transcription}`;
                if (checkImage && result.image) {
                    checkImage.src = result.image;
                    checkImage.style.display = "block"; 
                }
            }
        } catch (error) {
            console.error('Error processing audio:', error);
            statusText.innerText = `Error: ${error.message}`;
        }

        stream.getTracks().forEach(track => track.stop());
        audioChunks = [];
    };

    mediaRecorder.stop();
});


async function sendPartialAudio(chunks) {
    console.log('sendPartialAudio disabled to prevent overwriting');
}
