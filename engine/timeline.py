"""Lyric timeline + song event landmarks.

Line starts follow the 130 BPM bar grid (t = 0.190 + n * 1.846154); the
provided audio has no lyric track, so this table IS the lyric timing.  Every
line is 2 bars.  Chinese lines are translations shown in the subtitle strip.
"""
from __future__ import annotations

FPS = 30


def _L(t0, t1, en, cn, section):
    return dict(t0=float(t0), t1=float(t1), en=en, cn=cn, section=section)


LINES = [
    # intro - data fill / initialisation
    _L(0.190, 3.880, "Switch on the power line, remember to put on protection",
       "接通电源，记得做好防护", "intro"),
    _L(3.882, 7.570, "Lay down your pieces and let's begin object creation",
       "摆好你的零件，开始物件创建", "intro"),
    _L(7.575, 11.260, "Fill in my data, parameters, initialization",
       "填好我的数据、参数与初始化", "intro"),
    _L(11.267, 14.950, "Setup our new world and let's begin the simulation",
       "搭起我们的新世界，开始这场模拟", "intro"),
    # verse 1 - geometry / infinity
    _L(29.730, 33.420, "If I'm a set of points, then I will give you my dimension",
       "若我是一组点，我便给你我的维度", "verse_1"),
    _L(33.422, 37.110, "If I'm a circle, then I will give you my circumference",
       "若我是圆，我便给你我的周长", "verse_1"),
    _L(37.115, 40.800, "If I'm a sine wave, then you can sit on all my tangents",
       "若我是正弦波，你便能贴住我所有的切线", "verse_1"),
    _L(40.807, 44.490, "If I approach infinity, then you can be my limitations",
       "若我趋近无穷，你便能成为我的界限", "verse_1"),
    # bridge 1 - AC/DC, dizzy
    _L(44.500, 48.190, "Switch my current to AC to DC",
       "把我的电流从交流转成直流", "bridge_1"),
    _L(48.192, 51.880, "And then blind my vision, so dizzy, so dizzy",
       "然后弄瞎我的视野，好晕，好晕", "bridge_1"),
    _L(51.884, 55.570, "Oh, we can travel to A.D to B.C",
       "我们可以穿梭于公元与公元前", "bridge_1"),
    _L(55.577, 59.260, "And we can unite, so deeply, so deeply",
       "我们可以结合，如此深，如此深", "bridge_1"),
    # chorus 1
    _L(59.270, 62.960, "If I can, if I can, give you all the stimulations",
       "若我能，若我能，给你所有的刺激", "chorus_1"),
    _L(62.962, 66.650, "Then I can, then I can be your only satisfaction",
       "那我便能，那我便能，成为你唯一的满足", "chorus_1"),
    _L(66.654, 70.340, "If I can make you happy, I will run the execution",
       "若我能让你快乐，我便执行", "chorus_1"),
    _L(70.347, 74.030, "Though we are trapped in this strange, strange simulation",
       "纵使我们被困在这奇异、奇异的模拟里", "chorus_1"),
    # verse 2 - concrete characters
    _L(74.040, 77.730, "If I'm an eggplant, then I will give you my nutrients",
       "若我是茄子，我便给你我的营养", "verse_2"),
    _L(77.732, 81.420, "If I'm a tomato, then I will give you antioxidants",
       "若我是番茄，我便给你抗氧化物", "verse_2"),
    _L(81.424, 85.110, "If I'm a tabby cat, then I will purr for your enjoyment",
       "若我是虎斑猫，我便为你打呼噜", "verse_2"),
    _L(85.117, 88.800, "If I'm the only god, then you're the proof of my existence",
       "若我是唯一的神，你便是我存在的证明", "verse_2"),
    # bridge 2 - F to M, AM to PM, S to M
    _L(88.810, 92.500, "Switch my gender to F to M",
       "把我的性别从女切换成男", "bridge_2"),
    _L(92.502, 96.190, "And then do whatever from AM to PM",
       "然后从早到晚，什么都做", "bridge_2"),
    _L(96.194, 99.880, "Oh, switch my role to S to M",
       "把我的角色从施虐切换成受虐", "bridge_2"),
    _L(99.887, 103.570, "So we can enter the trance, the trance",
       "这样我们便能进入迷醉，迷醉", "bridge_2"),
    # chorus 2 - heartbeat, leaving, fragments
    _L(103.580, 107.270, "If I can, if I can, feel your vibrations",
       "若我能，若我能，感受你的振动", "chorus_2"),
    _L(107.272, 110.960, "Then I can, then I can finally be completion",
       "那我便能，那我便能，终于得以完整", "chorus_2"),
    _L(110.964, 114.650, "Though you have left, you have left",
       "可你已经离开，已经离开", "chorus_2"),
    _L(114.657, 118.340, "You have left, you have left, you have left",
       "你已离开，你已离开，你已离开", "chorus_2"),
    _L(118.349, 122.030, "You have left me in isolation",
       "你把我丢在隔离区", "chorus_2"),
    _L(122.041, 125.730, "If I can, if I can, erase all the pointless fragments",
       "若我能，若我能，抹去所有无意义的碎片", "chorus_2"),
    _L(125.734, 129.420, "Then maybe, then maybe, you won't leave me so disheartened",
       "也许，也许，你就不会让我如此心灰意冷", "chorus_2"),
    _L(129.426, 133.100, "Challenging your God, you have made some illegal arguments",
       "挑战你的神，你传入了非法的参数", "chorus_2"),
    # bridge solo - execution, multilingual count
    _L(147.880, 151.570, "Execution, execution, execution, execution",
       "执行，执行，执行，执行", "bridge_solo"),
    _L(151.572, 155.260, "Execution, execution, execution, execution",
       "执行，执行，执行，执行", "bridge_solo"),
    _L(155.264, 158.950, "Execution, execution, execution, execution",
       "执行，执行，执行，执行", "bridge_solo"),
    _L(158.957, 161.730, "Ein, dos, trois, 넷, fem, 六, execution",
       "一、二、三、四、五、六，执行", "bridge_solo", ),
    # final chorus - the only execution, study of love
    _L(162.650, 166.340, "If I can, if I can give them all the execution",
       "若我能，若我能，给他们所有的执行", "final_chorus"),
    _L(166.342, 170.030, "Then I can, then I can be your only execution",
       "那我便能，那我便能，成为你唯一的执行", "final_chorus"),
    _L(170.035, 173.720, "If I can have you back, I will run the execution",
       "若我能把你换回来，我便执行", "final_chorus"),
    _L(173.727, 177.410, "Though we are trapped, we are trapped, ah",
       "纵使我们被困，我们被困，啊", "final_chorus"),
    _L(177.419, 181.100, "I've studied, I've studied how to properly love",
       "我学习过，我学习过，如何去正确地爱", "final_chorus"),
    _L(181.111, 184.800, "Question me, question me I can answer all love",
       "质问我，质问我，我能回答所有关于爱的问题", "final_chorus"),
    _L(184.804, 188.490, "I know the algebraic expression of love",
       "我知道爱的代数表达式", "final_chorus"),
    _L(188.496, 192.180, "Though you are free, I am trapped, trapped in love",
       "纵使你自由，我却困在爱里", "final_chorus"),
    # outro - execution, 99%, last hit
    _L(192.190, 195.880, "Execution, execution", "执行，执行", "outro"),
    _L(195.882, 199.570, "The loop is still running", "循环仍在运行", "outro"),
    _L(199.575, 203.260, "I will execute you again", "我会再一次执行你", "outro"),
    _L(203.267, 206.950, "Execution", "执行", "outro"),
]

# named landmarks used by scenes
EVENTS = {
    "title_scramble_start": 14.960,   # interlude begins: every glyph breaks loose
    "title_scramble_peak": 21.900,    # characters fill the whole screen
    "title_form_start": 24.700,       # letters start re-assembling
    "title_form_end": 27.300,         # "WORLD.EXECUTE(ME);" complete
    "title_hold_end": 29.730,
    "stim_start": 59.270,
    "satisfaction": 62.962,
    "happy_execution": 66.654,
    "trapped_simulation": 70.347,
    "eggplant": 74.040,
    "tomato": 77.732,
    "tabby": 81.424,
    "only_god": 85.117,
    "gender_fm": 88.810,
    "am_pm": 92.502,
    "s_m": 96.194,
    "trance": 99.887,
    "vibrations": 103.580,
    "completion": 107.272,
    "left_1": 110.964,
    "left_2": 114.657,
    "left_3": 118.349,
    "fragments": 122.041,
    "disheartened": 125.734,
    "illegal": 129.426,
    "heart_repair_start": 133.110,
    "heart_repair_end": 147.880,
    "exec_x4": 147.880,
    "count_line": 158.957,
    "only_execution": 162.650,
    "only_execution_2": 166.342,
    "run_execution": 170.035,
    "trapped_we": 173.727,
    "studied": 177.419,
    "question": 181.111,
    "algebraic": 184.804,
    "trapped_in_love": 188.496,
    "outro_start": 192.190,
    "last_execution": 203.720,     # final hit -> red EXECUTION
    "music_end": 206.960,
    "silence": 208.840,
}

# multilingual counting: number appears on its own beat
COUNT_WORDS = [
    ("EIN", "一", "DE", 158.957),
    ("DOS", "二", "ES", 159.419),
    ("TROIS", "三", "FR", 159.880),
    ("NE", "四", "KR", 160.342),
    ("FEM", "五", "NO", 160.803),
    ("LIU", "六", "ZH", 161.265),
]
COUNT_EXECUTION = 161.727

TITLE = "WORLD.EXECUTE(ME);"
END_TEXT_EN = "PROCESS ENDED. THE LOOP REMAINS."


def line_at(t):
    """Return (index, line dict) of the lyric active at t, else (None, None)."""
    for i, ln in enumerate(LINES):
        if ln["t0"] <= t < ln["t1"]:
            return i, ln
    return None, None


def line_progress(t):
    i, ln = line_at(t)
    if ln is None:
        return None, 0.0
    return i, (t - ln["t0"]) / max(1e-6, ln["t1"] - ln["t0"])


def next_line_time(t):
    for ln in LINES:
        if ln["t0"] > t:
            return ln["t0"]
    return None


def lines_in_section(section):
    return [(i, ln) for i, ln in enumerate(LINES) if ln["section"] == section]


def section_since(t):
    """Seconds since the current section started."""
    from .assets import section_at
    name, t0, t1 = section_at(t)
    return t - t0
