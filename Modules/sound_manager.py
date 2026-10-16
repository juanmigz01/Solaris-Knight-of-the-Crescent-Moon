import json
import os
import pygame


class SoundManager:

    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        try:
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(6)
        except Exception:
            pass

        self.sfx_enabled = True
        self.bgm_enabled = True
        self.radius_visible = True
        self.outline_enabled = True
        self.hitbox_visible = False
        self.zones_visible = False
        self.particle_intensity = "medium"
        self.zoom_level = 1.0
        self.music_volume = 0.5
        self.sfx_volume = 0.5
        self.current_track = None

        self.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), ".."))
        self.saves_dir = os.path.join(self.project_root, "saves")
        self.settings_file = os.path.join(self.saves_dir, "setting.json")

        self._sfx_cache = {}
        self._loop_channels = {
            "text": pygame.mixer.Channel(3),
            "walk": pygame.mixer.Channel(4),
            "run":  pygame.mixer.Channel(5),
        }
        self._loop_sounds = {}

        self._ambient_track  = None
        self._ambient_volume = 0.25

        self._debug_reported_missing = set()
        self._debug_reported_loops   = set()

        self.load_settings()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                    self.sfx_enabled = data.get("sfx_enabled", True)
                    self.bgm_enabled = data.get("bgm_enabled", True)
                    self.radius_visible = data.get("radius_visible", True)
                    self.outline_enabled = data.get("outline_enabled", True)
                    self.hitbox_visible = data.get("hitbox_visible", False)
                    self.zones_visible = data.get("zones_visible", False)
                    self.particle_intensity = data.get("particle_intensity", "medium")
                    self.zoom_level = float(data.get("zoom_level", 1.0))
                    self.music_volume = float(data.get("music_volume", 0.5))
                    self.sfx_volume = float(data.get("sfx_volume", 0.5))
                pygame.mixer.music.set_volume(
                    self.music_volume if self.bgm_enabled else 0.0)
            except Exception as e:
                print(f"[SoundManager] Failed to load setting.json: {e}")

    def save_settings(self):
        try:
            os.makedirs(self.saves_dir, exist_ok=True)
            data = {
                "sfx_enabled": self.sfx_enabled,
                "bgm_enabled": self.bgm_enabled,
                "radius_visible": self.radius_visible,
                "outline_enabled": self.outline_enabled,
                "hitbox_visible": self.hitbox_visible,
                "zones_visible": self.zones_visible,
                "particle_intensity": self.particle_intensity,
                "zoom_level": round(self.zoom_level, 2),
                "music_volume": round(self.music_volume, 2),
                "sfx_volume": round(self.sfx_volume, 2),
            }
            with open(self.settings_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[SoundManager] Failed to save setting.json: {e}")

    def toggle_sfx(self):
        self.sfx_enabled = not self.sfx_enabled
        if not self.sfx_enabled:
            self.stop_all_sfx()
        self.save_settings()

    def toggle_bgm(self):
        self.bgm_enabled = not self.bgm_enabled
        if not self.bgm_enabled:
            pygame.mixer.music.set_volume(0.0)
        else:
            pygame.mixer.music.set_volume(self.music_volume)
            if self.current_track and not pygame.mixer.music.get_busy():
                self.play_music(os.path.basename(self.current_track), fade_ms=500)
        self.save_settings()

    def toggle_radius_visibility(self):
        self.radius_visible = not self.radius_visible
        self.save_settings()

    def toggle_outline_enabled(self):
        self.outline_enabled = not self.outline_enabled
        self.save_settings()

    def toggle_hitboxes(self):
        self.hitbox_visible = not self.hitbox_visible
        self.save_settings()

    def toggle_zones_visible(self):
        self.zones_visible = not self.zones_visible
        self.save_settings()

    PARTICLE_ORDER = ["off", "low", "medium", "high"]

    def cycle_particle_intensity(self):
        current = self.particle_intensity
        if current not in self.PARTICLE_ORDER:
            current = "medium"
        idx = self.PARTICLE_ORDER.index(current)
        self.particle_intensity = self.PARTICLE_ORDER[
            (idx + 1) % len(self.PARTICLE_ORDER)]
        self.save_settings()

    ZOOM_PRESETS = [1.0, 1.25, 1.5, 2.0]

    def cycle_zoom(self):
        current = round(self.zoom_level, 2)
        if current in self.ZOOM_PRESETS:
            index = self.ZOOM_PRESETS.index(current)
        else:
            index = 0
        next_index = (index + 1) % len(self.ZOOM_PRESETS)
        self.zoom_level = self.ZOOM_PRESETS[next_index]
        self.save_settings()

    def set_zoom(self, value):
        value = max(self.ZOOM_PRESETS[0], min(self.ZOOM_PRESETS[-1], float(value)))
        self.zoom_level = round(value, 2)
        self.save_settings()

    def change_music_volume(self, delta: float):
        self.music_volume = round(max(0.0, min(1.0, self.music_volume + delta)), 2)
        if self.bgm_enabled:
            pygame.mixer.music.set_volume(self.music_volume)
        self.save_settings()

    def change_sfx_volume(self, delta: float):
        self.sfx_volume = round(max(0.0, min(1.0, self.sfx_volume + delta)), 2)
        self.save_settings()

    def set_music_volume(self, volume: float):
        self.music_volume = max(0.0, min(1.0, volume))
        if self.bgm_enabled:
            pygame.mixer.music.set_volume(self.music_volume)
        self.save_settings()

    def set_sfx_volume(self, volume: float):
        self.sfx_volume = max(0.0, min(1.0, volume))
        self.save_settings()

    def _load_sfx(self, name):
        if not name:
            return None
        if name in self._sfx_cache:
            return self._sfx_cache[name]
        path = os.path.join(self.project_root, "asset", "sfx", name)
        if not os.path.exists(path):
            path = name
        if not os.path.exists(path):
            if name not in self._debug_reported_missing:
                self._debug_reported_missing.add(name)
                print(f"[SoundManager] SFX NOT FOUND: {name} "
                      f"(looked in asset/sfx/)")
            return None
        try:
            snd = pygame.mixer.Sound(path)
            self._sfx_cache[name] = snd
            return snd
        except Exception as e:
            print(f"[SoundManager] Failed loading SFX {name}: {e}")
            return None

    def play_sfx(self, name, volume=None):
        if not self.sfx_enabled:
            return
        snd = self._load_sfx(name)
        if snd is None:
            return
        vol = volume if volume is not None else self.sfx_volume
        try:
            snd.set_volume(vol)
            snd.play()
        except Exception as e:
            print(f"[SoundManager] play_sfx({name}) failed: {e}")

    def play_sfx_loop(self, key, name, volume=None):
        if not self.sfx_enabled:
            return
        ch = self._loop_channels.get(key)
        if ch is None:
            print(f"[SoundManager] No loop channel for key '{key}'")
            return
        snd = self._load_sfx(name)
        if snd is None:
            return
        if self._loop_sounds.get(key) is snd and ch.get_busy():
            return
        vol = volume if volume is not None else self.sfx_volume
        try:
            ch.set_volume(vol)
            ch.play(snd, loops=-1)
            self._loop_sounds[key] = snd
            if key not in self._debug_reported_loops:
                self._debug_reported_loops.add(key)
                print(f"[SoundManager] Loop SFX started: key='{key}' "
                      f"file='{name}' vol={vol:.2f}")
        except Exception as e:
            print(f"[SoundManager] play_sfx_loop({key}, {name}) failed: {e}")

    def stop_sfx(self, key):
        ch = self._loop_channels.get(key)
        if ch is not None:
            try:
                ch.stop()
            except Exception:
                pass
        self._loop_sounds.pop(key, None)

    def stop_all_sfx(self):
        for key in list(self._loop_channels.keys()):
            self.stop_sfx(key)

    def play_ambient(self, track_filename, volume=0.25, fade_ms=800):
        self._ambient_track  = track_filename
        self._ambient_volume = volume
        self.play_music(track_filename, fade_ms=fade_ms, volume=volume)

    def resume_ambient(self, fade_ms=600):
        if not self._ambient_track:
            return
        self.play_music(self._ambient_track, fade_ms=fade_ms,
                        volume=self._ambient_volume)

    def stop_ambient(self, fade_ms=500):
        self._ambient_track = None
        self.stop_music(fade_ms=fade_ms)

    def play_music(self, track_filename, loop: int = -1, fade_ms: int = 1000,
                   volume=None):
        track_path = os.path.join(self.project_root, "asset", "sfx", track_filename)
        if not os.path.exists(track_path):
            track_path = track_filename
        if not os.path.exists(track_path):
            print(f"[SoundManager] Audio file not found: {track_path}")
            return
        if self.current_track == track_path and pygame.mixer.music.get_busy():
            return
        try:
            if pygame.mixer.music.get_busy() and fade_ms > 0:
                pygame.mixer.music.fadeout(fade_ms)
                pygame.time.wait(int(fade_ms * 0.2))
            pygame.mixer.music.load(track_path)
            if volume is not None:
                actual_vol = float(volume) if self.bgm_enabled else 0.0
            else:
                actual_vol = self.music_volume if self.bgm_enabled else 0.0
            pygame.mixer.music.set_volume(actual_vol)
            pygame.mixer.music.play(loops=loop, fade_ms=fade_ms)
            self.current_track = track_path
        except Exception as e:
            print(f"[SoundManager] Failed to play music {track_filename}: {e}")

    def stop_music(self, fade_ms: int = 1000):
        if pygame.mixer.music.get_busy():
            if fade_ms > 0:
                pygame.mixer.music.fadeout(fade_ms)
            else:
                pygame.mixer.music.stop()
        self.current_track = None


game_manager = SoundManager()