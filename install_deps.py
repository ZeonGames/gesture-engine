import subprocess, sys
packages = [
    'mediapipe', 'opencv-python', 'pyautogui', 'pynput', 'numpy',
    'matplotlib', 'scipy', 'Pillow',
]
for pkg in packages:
    print(f'Installing {pkg}...')
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', pkg, '--quiet'],
                          capture_output=True, text=True, timeout=120)
    if result.returncode == 0:
        print(f'  OK: {pkg}')
    else:
        print(f'  FAILED: {pkg}')
        print(result.stderr[-300:] if result.stderr else 'no error')
print('Done!')
