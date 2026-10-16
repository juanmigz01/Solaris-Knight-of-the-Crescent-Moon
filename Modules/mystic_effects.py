

RAINBOW_COLORS = [
    (255,  80,  80),
    (255, 150,  60),
    (255, 230, 100),
    (120, 240, 120),
    (100, 220, 240),
    (110, 140, 255),
    (200, 110, 240),
]


class RainbowOutlinePulse:


    def __init__(self, colors=None, cycle_sec=12.0):
        self.colors = list(colors) if colors else list(RAINBOW_COLORS)
        self.num_colors = max(1, len(self.colors))
        self.cycle_sec = max(0.1, float(cycle_sec))
        self.time = 0.0

    def update(self, dt):
        self.time += dt
        if self.time >= self.cycle_sec:
            self.time %= self.cycle_sec

    def current_blend(self):

        phase = (self.time / self.cycle_sec) * self.num_colors
        a = int(phase) % self.num_colors
        b = (a + 1) % self.num_colors
        t = phase - int(phase)
        return a, b, t

    def draw_kwargs(self, obj):

        if not getattr(obj, "_variants", None):
            return {}
        a, b, t = self.current_blend()
        return {"blend_a": a, "blend_b": b, "blend_t": t}