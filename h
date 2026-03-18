[1mdiff --git a/.env.example b/.env.example[m
[1mindex daeffe9..de9b598 100644[m
[1m--- a/.env.example[m
[1m+++ b/.env.example[m
[36m@@ -1,10 +1,10 @@[m
 # API keys[m
[31m-DEEPSEEK_API_KEY=your_deepseek_api_key_here[m
[32m+[m[32mDEEPSEEK_API_KEY=sk-94f98c13075d4430a69be955d7d89ef0[m
 DEEPSEEK_BASE_URL=https://api.deepseek.com[m
 DEEPSEEK_MODEL=deepseek-chat[m
 [m
[31m-BAIDU_API_KEY=your_baidu_api_key_here[m
[31m-BAIDU_SECRET_KEY=your_baidu_secret_key_here[m
[32m+[m[32mBAIDU_API_KEY=Uk52iXfgR0J6kvo7MTAJYhfc[m
[32m+[m[32mBAIDU_SECRET_KEY=fsWeCc6p2AhpZUfVi4w40CiAggEe0ocu[m
 [m
 # Runtime[m
 DEBUG=false[m
[1mdiff --git a/config/__init__.py b/config/__init__.py[m
[1mindex b41f942..0b94ddb 100644[m
[1m--- a/config/__init__.py[m
[1m+++ b/config/__init__.py[m
[36m@@ -2,6 +2,7 @@[m
 配置模块导出。[m
 """[m
 [m
[32m+[m[32mfrom .settings import settings[m
 from .api_config import api_config[m
 from .audio_config import audio_config[m
 from .dance_config import dance_config[m
[36m@@ -12,7 +13,6 @@[m [mfrom .runtime_config import ([m
     TransportMode,[m
     build_runtime_profile,[m
 )[m
[31m-from .settings import settings[m
 [m
 __all__ = [[m
     "api_config",[m
[1mdiff --git a/core/choreographer.py b/core/choreographer.py[m
[1mindex 8f3964c..642c431 100644[m
[1m--- a/core/choreographer.py[m
[1m+++ b/core/choreographer.py[m
[36m@@ -31,12 +31,15 @@[m [mclass MarkovChain:[m
     [m
     # 动作类型之间的转移概率[m
     TYPE_TRANSITIONS = {[m
[31m-        "stand": {"forward": 0.35, "gesture": 0.25, "turn": 0.20, "side": 0.15, "stand": 0.05},[m
[31m-        "forward": {"turn": 0.30, "side": 0.25, "stand": 0.20, "gesture": 0.15, "forward": 0.10},[m
[31m-        "turn": {"forward": 0.35, "side": 0.25, "stand": 0.20, "gesture": 0.15, "turn": 0.05},[m
[31m-        "side": {"forward": 0.30, "turn": 0.25, "stand": 0.20, "gesture": 0.15, "side": 0.10},[m
[31m-        "gesture": {"forward": 0.30, "stand": 0.25, "turn": 0.20, "side": 0.15, "gesture": 0.10},[m
[31m-        "combo": {"stand": 0.40, "gesture": 0.25, "forward": 0.20, "turn": 0.10, "side": 0.05},[m
[32m+[m[32m        "stand":   {"forward": 0.30, "gesture": 0.20, "turn": 0.15, "side": 0.10, "dance": 0.15, "left": 0.05, "right": 0.05, "stand": 0.00},[m
[32m+[m[32m        "forward": {"turn": 0.20, "side": 0.15, "stand": 0.15, "gesture": 0.10, "dance": 0.25, "left": 0.10, "right": 0.05, "forward": 0.00},[m
[32m+[m[32m        "turn":    {"forward": 0.25, "side": 0.15, "stand": 0.15, "gesture": 0.10, "dance": 0.20, "left": 0.10, "right": 0.05, "turn": 0.00},[m
[32m+[m[32m        "side":    {"forward": 0.20, "turn": 0.20, "stand": 0.15, "gesture": 0.10, "dance": 0.20, "left": 0.10, "right": 0.05, "side": 0.00},[m
[32m+[m[32m        "gesture": {"forward": 0.20, "stand": 0.15, "turn": 0.15, "side": 0.10, "dance": 0.25, "left": 0.10, "right": 0.05, "gesture": 0.00},[m
[32m+[m[32m        "combo":   {"stand": 0.25, "gesture": 0.20, "forward": 0.15, "turn": 0.10, "dance": 0.20, "left": 0.05, "right": 0.05, "side": 0.00},[m
[32m+[m[32m        "dance":   {"dance": 0.35, "gesture": 0.20, "forward": 0.15, "stand": 0.10, "left": 0.10, "right": 0.05, "turn": 0.05, "side": 0.00},[m
[32m+[m[32m        "left":    {"right": 0.35, "dance": 0.30, "forward": 0.15, "stand": 0.10, "gesture": 0.05, "turn": 0.05, "side": 0.00, "left": 0.00},[m
[32m+[m[32m        "right":   {"left": 0.35, "dance": 0.30, "forward": 0.15, "stand": 0.10, "gesture": 0.05, "turn": 0.05, "side": 0.00, "right": 0.00},[m
     }[m
     [m
     def __init__(self):[m
[36m@@ -268,7 +271,7 @@[m [mclass Choreographer:[m
     def _score_mood_match(self, action, music_features: MusicFeatures) -> float:[m
         """情绪匹配评分"""[m
         if music_features.mood == "energetic":[m
[31m-            return 1.0 if hasattr(action, 'type') and action.type in ["forward", "combo"] else 0.5[m
[32m+[m[32m            return 1.0 if hasattr(action, 'type') and action.type in ["forward", "combo", "dance", "left", "right"] else 0.5[m
         elif music_features.mood == "calm":[m
             return 1.0 if hasattr(action, 'type') and action.type in ["stand", "gesture"] else 0.5[m
         return 0.7[m
[36m@@ -285,9 +288,9 @@[m [mclass Choreographer:[m
         # 不同段落偏好不同类型的动作[m
         preferences = {[m
             "intro": ["stand", "gesture"],[m
[31m-            "verse": ["forward", "side"],[m
[31m-            "chorus": ["combo", "forward"],[m
[31m-            "bridge": ["turn", "side"],[m
[32m+[m[32m            "verse": ["forward", "side", "left", "right"],[m
[32m+[m[32m            "chorus": ["combo", "forward", "dance"],[m
[32m+[m[32m            "bridge": ["turn", "side", "left", "right", "dance"],[m
             "outro": ["stand", "gesture"],[m
         }[m
         [m
[36m@@ -386,6 +389,9 @@[m [mclass Choreographer:[m
                 "side": "侧移动作",[m
                 "gesture": "手势动作",[m
                 "combo": "组合动作",[m
[32m+[m[32m                "dance": "舞蹈动作",[m
[32m+[m[32m                "left": "左移动作",[m
[32m+[m[32m                "right": "右移动作",[m
             }[m
             reasons.append(type_names.get(action.type, action.type))[m
         [m
[1mdiff --git a/core/music_analyzer.py b/core/music_analyzer.py[m
[1mindex 2aca169..80ed844 100644[m
[1m--- a/core/music_analyzer.py[m
[1m+++ b/core/music_analyzer.py[m
[36m@@ -123,7 +123,7 @@[m [mclass MusicAnalyzer:[m
         self.stream = None[m
 [m
         # 降低环境噪音误触发，同时缩短首次有效输入等待。[m
[31m-        self.noise_threshold = 250[m
[32m+[m[32m        self.noise_threshold = 10[m
         self.valid_signal_count = 0[m
         self.required_valid_frames = 2[m
         [m
[36m@@ -150,6 +150,10 @@[m [mclass MusicAnalyzer:[m
             logger.error("pyaudio 不可用，无法进行音乐分析")[m
             return False[m
         [m
[32m+[m[32m        # 重置特征状态，防止旧数据欺骗 _wait_for_music_ready[m
[32m+[m[32m        self.current_features = MusicFeatures()[m
[32m+[m[32m        self.features_history.clear()[m
[32m+[m
         try:[m
             # 初始化音频设备[m
             self.audio = pyaudio.PyAudio()[m
[36m@@ -314,11 +318,17 @@[m [mclass MusicAnalyzer:[m
     def _extract_features(self, audio_data: np.ndarray) -> MusicFeatures:[m
         """提取音乐特征"""[m
         features = MusicFeatures()[m
[31m-        features.timestamp = time.time()[m
[31m-        [m
[32m+[m
[32m+[m[32m        # 数据不足 0.5 秒时，直接返回空特征，不更新 timestamp[m
[32m+[m[32m        min_required_length = int(self.sample_rate * 0.5)[m
[32m+[m[32m        if len(audio_data) < min_required_length:[m
[32m+[m[32m            return features[m
[32m+[m
         try:[m
[31m-            # 基础特征[m
[31m-            features.energy = float(np.mean(audio_data ** 2))[m
[32m+[m[32m            # 使用 RMS 计算 energy，确保量级与外部阈值（0.001）匹配[m
[32m+[m[32m            raw_energy = float(np.sqrt(np.mean(audio_data ** 2)))[m
[32m+[m[32m            features.energy = raw_energy if np.isfinite(raw_energy) else 0.0[m
[32m+[m
             features.zero_crossing_rate = float([m
                 np.mean(librosa.feature.zero_crossing_rate(audio_data)[0])[m
             )[m
[36m@@ -364,11 +374,14 @@[m [mclass MusicAnalyzer:[m
         except Exception as e:[m
             logger.warning(f"特征提取错误: {e}")[m
             features.tempo = 120.0[m
[31m-            features.energy = 0.1[m
[32m+[m[32m            features.energy = 0.0[m
             features.rhythm_pattern = "steady"[m
             features.mood = "neutral"[m
             features.confidence = 0.3[m
[31m-        [m
[32m+[m[32m            return features[m
[32m+[m
[32m+[m[32m        # 所有计算完成后再打 timestamp，避免 librosa 耗时导致时间戳过期[m
[32m+[m[32m        features.timestamp = time.time()[m
         return features[m
     [m
     def _analyze_rhythm_pattern(self, features: MusicFeatures) -> str:[m
[1mdiff --git a/data/actions.csv b/data/actions.csv[m
[1mindex 280d8fb..11c5b2e 100644[m
[1m--- a/data/actions.csv[m
[1m+++ b/data/actions.csv[m
[36m@@ -1,10 +1,42 @@[m
 seq,title,label,time_ms,beats,type,energy,tempo_match[m
 000,初始化,招左手,4000,4,gesture,low,any[m
[31m-001,立正,立正,1000,1,stand,low,slow[m
[31m-002,大创前进,前进,7500,8,forward,high,fast[m
[31m-003,全动作汇总,全动作汇总,211000,211,combo,high,any[m
[31m-004,右侧移,右侧移,5600,6,side,medium,medium[m
[31m-005,左侧移,左侧移,5800,6,side,medium,medium[m
[31m-006,大字站立,大字站立,6000,6,stand,medium,slow[m
[31m-007,左上右下,左上右下,5000,5,gesture,medium,medium[m
[31m-008,左转,左转,5300,5,turn,medium,medium[m
[32m+[m[32m001,立正,立正,2000,1,stand,low,slow[m
[32m+[m[32m002,双手摇摆,双手摇摆,5000,6,stand,high,fast[m
[32m+[m[32m003,挥舞双手,挥舞双手,9800,6,side,medium,medium[m
[32m+[m[32m004,欢快起舞,欢快起舞,3500,211,dance,high,any[m
[32m+[m[32m005,前挥手,前挥手,5000,6,gesture,medium,medium[m
[32m+[m[32m006,比心,比心,5800,50,gesture,high,fast[m
[32m+[m[32m007,挥左拳,挥左拳,3100,5,gesture,high,fast[m
[32m+[m[32m008,挥右拳,挥右拳,3600,5,gesture,medium,medium[m
[32m+[m[32m009,挥右手,挥右手,5000,5,gesture,medium,medium[m
[32m+[m[32m010,左右摇摆,左右摇摆,5500,20,dance,high,fast[m
[32m+[m[32m011,上下摆动,上下摆动,4800,211,dance,high,fast[m
[32m+[m[32m012,骑马,骑马,7000,211,dance,high,fast[m
[32m+[m[32m013,左右摇摆挥手,左右摇摆挥手,7200,211,dance,high,fast[m
[32m+[m[32m014,前进侧步,前进侧步,6400,8,forward,medium,medium[m
[32m+[m[32m015,奶龙舞,奶龙舞,6300,10,dance,high,fast[m
[32m+[m[32m016,抱头摇晃,抱头摇晃,7000,6,dance,low,slow[m
[32m+[m[32m017,金鸡独立,金鸡独立,6400,8,dance,medium,medium[m
[32m+[m[32m018,劈叉,劈叉,8000,10,dance,medium,medium[m
[32m+[m[32m019,侧踢,侧踢,8000,10,dance,high,fast[m
[32m+[m[32m020,俯卧撑,俯卧撑,13600,17,dance,high,fast[m
[32m+[m[32m021,博尔特摆动,博尔特摆动,4700,7,dance,high,fast[m
[32m+[m[32m022,左侧移,左侧移,4800,6,left,medium,medium[m
[32m+[m[32m023,右侧移,右侧移,4800,6,right,medium,medium[m
[32m+[m[32m024,左转弯,左转弯,4400,5,left,medium,medium[m
[32m+[m[32m025,右转弯,右转弯,4400,5,right,medium,medium[m
[32m+[m[32m026,饮酒,饮酒,6100,8,gesture,low,slow[m
[32m+[m[32m027,捶胸,捶胸,5600,7,gesture,low,slow[m
[32m+[m[32m028,波浪,波浪,3200,4,dance,high,fast[m
[32m+[m[32m029,挥手扭腰,挥手扭腰,6100,7,dance,high,fast[m
[32m+[m[32m030,伸腿舞手(慢),伸腿舞手(慢),7800,8,dance,low,slow[m
[32m+[m[32m031,原地踏步,原地踏步,5400,12,dance,high,fast[m
[32m+[m[32m032,大字伸展,大字伸展,6400,8,dance,high,fast[m
[32m+[m[32m033,铁山靠,铁山靠,5600,7,dance,high,fast[m
[32m+[m[32m034,扭腰摆手,扭腰摆手,6400,8,dance,high,fast[m
[32m+[m[32m035,上下摇摆挥手,上下摇摆挥手,6400,8,dance,high,fast[m
[32m+[m[32m036,扭腰,扭腰,5600,7,dance,high,fast[m
[32m+[m[32m037,捧腹大笑,捧腹大笑,6400,8,dance,high,slow[m
[32m+[m[32m038,迈步挥手,迈步挥手,5800,7,dance,high,fast[m
[32m+[m[32m039,坐下饮酒,坐下饮酒,14700,17,dance,low,slow[m
[32m+[m[32m040,左右跨步伸展,左右跨步伸展,8400,8,dance,high,low[m
\ No newline at end of file[m
