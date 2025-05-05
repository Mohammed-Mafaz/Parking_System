import cv2
import sys
import os

def resize_video(input_path: str, output_path: str, target_size=(1024, 768), target_fps=30):
    # Check if input file exists
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input video file '{input_path}' not found.")

    # Open input video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open input video '{input_path}'.")

    # Set output FPS to target_fps
    fps = target_fps
    fourcc_output = cv2.VideoWriter_fourcc(*'mp4v')  # codec for .mp4

    # Create VideoWriter for output
    out = cv2.VideoWriter(output_path, fourcc_output, fps, target_size)
    if not out.isOpened():
        cap.release()
        raise RuntimeError(f"Failed to open output video '{output_path}'. Check codec and file permissions.")

    print(f"Resizing '{input_path}' to {target_size} at {fps} FPS and saving as '{output_path}'...")

    # Process frames
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # Resize frame
        resized = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)
        # Write to output
        out.write(resized)

    # Release resources
    cap.release()
    out.release()
    print("Resizing complete.")

# if __name__ == '__main__':
#     if len(sys.argv) < 3:
#         print("Usage: python resize_video.py <input.mov> <output.mp4>")
#         sys.exit(1)

#     input_file = sys.argv[1]
#     output_file = sys.argv[2]
#     try:
#         resize_video(input_file, output_file)
#     except Exception as e:
#         print(f"Error: {e}")
#         sys.exit(1)

if __name__ == '__main__':
    base = os.path.dirname(__file__)  # script’s folder
    input_file = os.path.join(base, '', 'Parking-Section-Video.mp4')
    output_file = os.path.join(base, '', 'Parking-Section.mp4')
    resize_video(input_file, output_file)

