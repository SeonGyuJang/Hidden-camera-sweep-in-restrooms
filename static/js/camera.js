// Camera utility for inspection form
let currentTarget = null;   // 'before' | 'after'
let stream = null;
let facingMode = 'environment';

function triggerCapture(target) {
  // handled by explicit buttons; click on area does nothing extra
}

function openCamera(target) {
  currentTarget = target;
  const modal = document.getElementById('cameraModal');
  modal.classList.remove('d-none');
  document.getElementById('cameraLabel').textContent =
    target === 'before' ? '📷 점검 전 사진 촬영' : '📷 점검 후 사진 촬영';
  startStream();
}

function startStream() {
  if (stream) stopStream();
  navigator.mediaDevices.getUserMedia({
    video: { facingMode, width: { ideal: 1280 }, height: { ideal: 720 } }
  }).then(s => {
    stream = s;
    document.getElementById('cameraVideo').srcObject = s;
  }).catch(err => {
    console.error(err);
    alert('카메라를 사용할 수 없습니다. 파일 업로드를 이용해 주세요.');
    closeCamera();
  });
}

function stopStream() {
  if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
  const v = document.getElementById('cameraVideo');
  if (v) v.srcObject = null;
}

function switchCamera() {
  facingMode = facingMode === 'environment' ? 'user' : 'environment';
  startStream();
}

function capturePhoto() {
  const video = document.getElementById('cameraVideo');
  const canvas = document.getElementById('cameraCanvas');
  canvas.width = video.videoWidth || 1280;
  canvas.height = video.videoHeight || 720;
  canvas.getContext('2d').drawImage(video, 0, 0);
  const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
  setPhoto(currentTarget, dataUrl);
  closeCamera();
}

function closeCamera() {
  stopStream();
  document.getElementById('cameraModal').classList.add('d-none');
}

function handleFile(event, target) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => setPhoto(target, e.target.result);
  reader.readAsDataURL(file);
}

function setPhoto(target, dataUrl) {
  document.getElementById(target + 'Data').value = dataUrl;
  const preview = document.getElementById(target + 'Preview');
  preview.src = dataUrl;
  preview.style.display = 'block';
  document.getElementById(target + 'Placeholder').style.display = 'none';
}

function clearPhoto(target) {
  document.getElementById(target + 'Data').value = '';
  const preview = document.getElementById(target + 'Preview');
  preview.src = '';
  preview.style.display = 'none';
  document.getElementById(target + 'Placeholder').style.display = '';
  document.getElementById(target + 'File').value = '';
}
