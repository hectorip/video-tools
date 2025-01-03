import subprocess
import os
import sys

def remove_silence(input_file, output_file, noise_level="-30dB", duration="1.0"):
    """
    Remueve los silencios de un archivo MP4 usando ffmpeg.
    
    Args:
        input_file (str): Ruta del archivo MP4 de entrada
        output_file (str): Ruta donde se guardará el archivo procesado
        noise_level (str): Nivel de audio considerado como silencio (default: -30dB)
        duration (str): Duración mínima del silencio para ser removido (default: 0.5 segundos)
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"El archivo {input_file} no existe")

    # Detectar silencios
    detect_cmd = [
        'ffmpeg', '-i', input_file,
        '-af', f'silencedetect=noise={noise_level}:d={duration}',
        '-f', 'null', '-'
    ]
    result = subprocess.run(detect_cmd, capture_output=True, text=True)
    # Procesar la salida para obtener los intervalos sin silencio
    silence_starts = []
    silence_ends = []
    for line in result.stderr.split('\n'):
        if 'silence_start' in line:
            silence_starts.append(float(line.split('silence_start: ')[1].split()[0]))
        elif 'silence_end' in line:
            silence_ends.append(float(line.split('silence_end: ')[1].split()[0]))

    # Crear un archivo de filtro complejo para ffmpeg
    filter_file = "filter_complex.txt"
    with open(filter_file, 'w') as f:
        # Inicio del filtro complejo
        segments = []
        current_time = 0
        
        video_duration = float(subprocess.check_output([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', input_file
        ]).decode().strip())

        # Generar las partes del filtro para cada segmento no silencioso
        for i, (start, end) in enumerate(zip(silence_starts, silence_ends)):
            if start > current_time:
                segments.append(f"between(t,{current_time},{start})")
            current_time = end

        # Agregar el último segmento si es necesario
        if current_time < video_duration:
            segments.append(f"between(t,{current_time},{video_duration})")

        # Escribir el filtro complejo
        f.write(f"select='{'+'.join(segments)}',setpts=N/FRAME_RATE/TB[v];\n")
        f.write(f"aselect='{'+'.join(segments)}',asetpts=N/SR/TB[a]")

    # Ejecutar ffmpeg con el filtro complejo
    compress_cmd = [
        'ffmpeg', '-i', input_file,
        '-filter_complex_script', filter_file,
        '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'medium',
        '-c:a', 'aac', '-b:a', '192k',
        '-y', output_file
    ]

    try:
        subprocess.run(compress_cmd, check=True)
        print(f"Video procesado exitosamente.")
    finally:
        # Limpiar archivo temporal
        if os.path.exists(filter_file):
            os.remove(filter_file) 

if __name__ == "__main__":
    # Ejemplo de uso
    input_file = sys.argv[1]  # use the first argument as input file
    output_file = "video_sin_silencios.mp4"
    
    try:
        remove_silence(input_file, output_file)
        print(f"Video procesado exitosamente. Guardado como: {output_file}")
    except Exception as e:
        print(f"Error al procesar el video: {str(e)}")
