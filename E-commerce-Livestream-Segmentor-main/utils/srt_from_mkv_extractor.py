import os
import subprocess
import re


def extract_srt_from_mkv(mkv_file_path, output_dir=None):
    """
    Extract SRT subtitles from an MKV file using ffmpeg.

    Args:
        mkv_file_path (str): Path to the MKV file
        output_dir (str, optional): Directory to save the SRT files. Defaults to same directory as MKV.

    Returns:
        list: Paths to extracted SRT files
    """
    if not os.path.exists(mkv_file_path):
        raise FileNotFoundError(f"MKV file not found: {mkv_file_path}")

    if output_dir is None:
        output_dir = os.path.dirname(mkv_file_path)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get information about the subtitles in the MKV file
    cmd = ["ffmpeg", "-i", mkv_file_path]
    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    output = result.stderr

    # Find subtitle streams
    subtitle_streams = []
    for line in output.splitlines():
        if "Stream" in line and "Subtitle" in line:
            stream_match = re.search(r"Stream #(\d+:\d+)(?:\((\w+)\))?: Subtitle", line)
            if stream_match:
                stream_id = stream_match.group(1)
                language = stream_match.group(2) if stream_match.group(2) else "unknown"
                subtitle_streams.append((stream_id, language))

    if not subtitle_streams:
        print("No subtitle streams found in the MKV file.")
        return []

    # Extract each subtitle stream
    extracted_files = []
    base_name = os.path.splitext(os.path.basename(mkv_file_path))[0]

    for idx, (stream_id, language) in enumerate(subtitle_streams):
        output_file = os.path.join(output_dir, f"{base_name}.{language}.srt")

        # If file already exists, add a number to prevent overwriting
        if os.path.exists(output_file):
            output_file = os.path.join(output_dir, f"{base_name}.{language}.{idx}.srt")

        map_param = f"0:{stream_id.split(':')[1]}"
        cmd = [
            "ffmpeg",
            "-i", mkv_file_path,
            "-map", map_param,
            "-c:s", "srt",
            output_file
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Extracted subtitle to: {output_file}")
            extracted_files.append(output_file)
        except subprocess.CalledProcessError as e:
            print(f"Error extracting subtitle stream {stream_id}: {e}")

    return extracted_files


# Example usage
if __name__ == "__main__":
    # Replace with your MKV file path
    mkv_file = "D:/Download/Daredevil.Born.Again.S01E08.Isle.of.Joy.2160p.JSTAR.WEB-DL.DDP5.1.H.265-PrimeFix.mkv"
    extracted_srts = extract_srt_from_mkv(mkv_file)

    if extracted_srts:
        print(f"Successfully extracted {len(extracted_srts)} subtitle files.")