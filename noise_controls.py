# --- noise_controls.py ---
import numpy as np
import pygame
from scipy.signal import butter, lfilter

class NoiseController:
    def __init__(self, sample_rate=44100, duration=5.0, volume=0.4, noise_type='brown'):
        self.sample_rate = sample_rate
        self.duration = duration
        self.volume = volume
        self.noise_type = noise_type
        self.sound = None
        try:
            pygame.mixer.init(frequency=sample_rate, size=-16, channels=2)
            self.generate_noise()
            self.play()
            print(f"NoiseController: {self.noise_type.capitalize()} noise playback started")
        except Exception as e:
            print(f"NoiseController: Error initializing audio: {str(e)}")

    def lowpass_filter(self, data, cutoff=4000, order=6):
        nyq = 0.5 * self.sample_rate
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return lfilter(b, a, data)

    def generate_variable_lfo(self, t, min_freq=0.05, max_freq=0.15):
        """Genera un LFO no periódico interpolando entre frecuencias aleatorias."""
        n_points = 10
        rand_freqs = np.random.uniform(min_freq, max_freq, n_points)
        rand_phases = np.random.uniform(0, 2*np.pi, n_points)
        key_times = np.linspace(0, self.duration, n_points)
        freqs = np.interp(t, key_times, rand_freqs)
        phases = np.interp(t, key_times, rand_phases)
        lfo = 0.85 + 0.15 * np.sin(2 * np.pi * freqs * t + phases)
        return lfo

    def generate_noise(self):
        samples = int(self.sample_rate * self.duration)

        # Generar ruido base
        if self.noise_type == 'white':
            noise = np.random.uniform(-1, 1, samples)
        elif self.noise_type == 'pink':
            white = np.random.uniform(-1, 1, samples)
            pink = np.cumsum(white) / np.arange(1, samples + 1) ** 0.5
            noise = pink / np.max(np.abs(pink)) * 0.9
        elif self.noise_type == 'brown':
            white = np.random.uniform(-1, 1, samples)
            brown = np.cumsum(white)
            brown = brown / np.max(np.abs(brown)) * 0.9
            noise = self.lowpass_filter(brown, cutoff=4000)
        else:
            raise ValueError(f"Unsupported noise type: {self.noise_type}")

        # Tiempo
        t = np.linspace(0, self.duration, samples, endpoint=False)

        # LFO aleatorio interpolado
        mod = self.generate_variable_lfo(t)

        # Glitch sutil
        glitch = 1.0 + 0.02 * np.random.randn(samples)

        # Aplicar modulación y glitch
        noise *= mod * glitch

        # Normalizar y convertir a estéreo
        noise = noise / np.max(np.abs(noise)) * 0.9
        noise = (noise * 32767).astype(np.int16)
        stereo_noise = np.repeat(noise[:, np.newaxis], 2, axis=1)
        self.sound = pygame.mixer.Sound(stereo_noise.tobytes())

    def play(self):
        if self.sound:
            self.sound.set_volume(self.volume)
            self.sound.play(loops=-1)

    def stop(self):
        if self.sound:
            self.sound.stop()
        pygame.mixer.quit()

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        if self.sound:
            self.sound.set_volume(self.volume)
        print(f"NoiseController: Volume set to {self.volume:.2f}")

    def set_duration(self, duration):
        self.duration = max(1.0, duration)
        if self.sound:
            self.sound.stop()
        self.generate_noise()
        self.play()
        print(f"NoiseController: Duration set to {self.duration:.2f} seconds")

    def set_noise_type(self, noise_type):
        self.noise_type = noise_type
        if self.sound:
            self.sound.stop()
        self.generate_noise()
        self.play()
        print(f"NoiseController: Noise type set to {self.noise_type}")

# --- Ejemplo de uso ---
if __name__ == "__main__":
    nc = NoiseController()
    try:
        while True:
            pass  # Mantener el programa corriendo
    except KeyboardInterrupt:
        nc.stop()
        print("NoiseController: Playback stopped")
