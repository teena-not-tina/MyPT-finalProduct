# exercise_analyzer.py (The Brain)

# What it does: The core logic that analyzes your exercise form
# Think of it as: A personal trainer that watches your movements and counts reps
# Can't run alone - it's a module used by other files


import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import time

from types import SimpleNamespace


class Exercise(Enum):
    PUSHUP = "푸시업"
    SQUAT = "스쿼트"
    LEG_RAISE = "레그레이즈"
    DUMBBELL_CURL = "덤벨컬"
    ONE_ARM_ROW = "원암덤벨로우"
    PLANK = "플랭크"


@dataclass
class PostureFeedback:
    is_correct: bool
    feedback_messages: List[str]
    angle_data: Dict[str, float]
    confidence: float
    rep_quality: float = 1.0  # 0-1 score for rep quality


class ExerciseAnalyzer:
    def __init__(self, model_path: str = 'pose_landmarker_full.task'):
        """Initialize the exercise analyzer with MediaPipe pose detection."""
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            output_segmentation_masks=False,
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)
        
        # Smoothing parameters
        self.prev_landmarks = None
        self.alpha = 0.7  # Smoothing factor
        
        # Exercise state tracking
        self.rep_count = 0
        self.target_reps = None  # Will be set from routine
        self.exercise_state = "ready"  # ready, down, up
        self.on_exercise_complete = None  # Callback when target reps reached
        
        # Velocity tracking
        self.prev_angles = {}  # Track previous angles
        self.angle_history = []  # Track angle changes
        
        # Plank timer
        self.exercise_start_time = None
        self.hold_duration = 0
        
        # Form history tracking
        self.form_history = []  # Track form quality over time
        
    def calculate_angle(self, a, b, c):
        """
        Calculate the angle (in degrees) between three points.
        Points should be (x, y) or (x, y, z).
        """
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)

        ba = a - b
        bc = c - b

        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
        return np.degrees(angle)
    
    def set_target_reps(self, target: int, callback=None):
        """Set target rep count and optional completion callback."""
        self.target_reps = target
        self.on_exercise_complete = callback
    
    def check_completion(self):
        """Check if exercise is complete and trigger callback."""
        if self.target_reps and self.rep_count >= self.target_reps:
            if self.on_exercise_complete:
                self.on_exercise_complete()
            return True
        return False
    
    def get_landmark_coordinates(self, landmarks, idx: int) -> Tuple[float, float]:
        """Get (x, y) coordinates for a specific landmark."""
        landmark = landmarks[idx]
        return (landmark.x, landmark.y)
    
    def smooth_landmarks(self, current, previous, alpha: float):
        """Apply exponential moving average smoothing to landmarks."""
        if previous is None:
            return current
        
        smoothed = []
        for cur, prev in zip(current, previous):
            smoothed.append(
                type(cur)(
                    x=alpha * prev.x + (1 - alpha) * cur.x,
                    y=alpha * prev.y + (1 - alpha) * cur.y,
                    z=alpha * prev.z + (1 - alpha) * cur.z,
                    visibility=cur.visibility if hasattr(cur, 'visibility') else 0
                )
            )
        return smoothed
    
    def check_movement_speed(self, current_angle, angle_key, max_change=30):
        """Check if movement is too fast (prevents false counts)."""
        if angle_key in self.prev_angles:
            change = abs(current_angle - self.prev_angles[angle_key])
            if change > max_change:  # More than 30 degrees per frame is too fast
                return False
        self.prev_angles[angle_key] = current_angle
        return True
    
    def analyze_pushup(self, landmarks) -> PostureFeedback:
        """Enhanced pushup form analysis with better biomechanics"""
        # Get key points
        left_shoulder = self.get_landmark_coordinates(landmarks, 11)
        right_shoulder = self.get_landmark_coordinates(landmarks, 12)
        left_elbow = self.get_landmark_coordinates(landmarks, 13)
        right_elbow = self.get_landmark_coordinates(landmarks, 14)
        left_wrist = self.get_landmark_coordinates(landmarks, 15)
        right_wrist = self.get_landmark_coordinates(landmarks, 16)
        left_hip = self.get_landmark_coordinates(landmarks, 23)
        right_hip = self.get_landmark_coordinates(landmarks, 24)
        left_knee = self.get_landmark_coordinates(landmarks, 25)
        right_knee = self.get_landmark_coordinates(landmarks, 26)
        left_ankle = self.get_landmark_coordinates(landmarks, 27)
        right_ankle = self.get_landmark_coordinates(landmarks, 28)
        
        feedback_messages = []
        is_correct = True
        
        # Calculate midpoints
        mid_shoulder = ((left_shoulder[0] + right_shoulder[0]) / 2, 
                    (left_shoulder[1] + right_shoulder[1]) / 2)
        mid_hip = ((left_hip[0] + right_hip[0]) / 2, 
                (left_hip[1] + right_hip[1]) / 2)
        mid_ankle = ((left_ankle[0] + right_ankle[0]) / 2, 
                    (left_ankle[1] + right_ankle[1]) / 2)
        mid_wrist = ((left_wrist[0] + right_wrist[0]) / 2,
                    (left_wrist[1] + right_wrist[1]) / 2)
        
        # 1. POSITION VALIDATION - Must be in pushup position
        body_horizontal = abs(mid_shoulder[1] - mid_hip[1]) < 0.2
        hands_on_ground = mid_wrist[1] > mid_shoulder[1]  # Wrists below shoulders
        
        if not body_horizontal:
            return PostureFeedback(
                is_correct=False,
                feedback_messages=["푸시업 자세를 취하세요 - 몸을 수평으로 만드세요"],
                angle_data={"rep_count": self.rep_count},
                confidence=0.5,
                rep_quality=0.0
            )
        
        if not hands_on_ground:
            return PostureFeedback(
                is_correct=False,
                feedback_messages=["손을 바닥에 대고 푸시업 자세를 취하세요"],
                angle_data={"rep_count": self.rep_count},
                confidence=0.5,
                rep_quality=0.0
            )
        
        # 2. FORM ANALYSIS
        # Calculate elbow angles
        left_elbow_angle = self.calculate_angle(left_shoulder, left_elbow, left_wrist)
        right_elbow_angle = self.calculate_angle(right_shoulder, right_elbow, right_wrist)
        avg_elbow_angle = (left_elbow_angle + right_elbow_angle) / 2
        
        # Body alignment (should be straight line)
        body_alignment_angle = self.calculate_angle(mid_shoulder, mid_hip, mid_ankle)
        alignment_deviation = abs(body_alignment_angle - 180)
        
        # Hand positioning (should be about shoulder width)
        hand_width = abs(left_wrist[0] - right_wrist[0])
        shoulder_width = abs(left_shoulder[0] - right_shoulder[0])
        hand_width_ratio = hand_width / (shoulder_width + 0.01)  # Avoid division by zero
        
        # 3. FORM FEEDBACK
        if alignment_deviation > 20:
            if body_alignment_angle < 160:
                feedback_messages.append("엉덩이를 내리세요 - 몸을 일직선으로 유지")
            else:
                feedback_messages.append("엉덩이를 올리세요 - 몸이 처지지 않게")
            is_correct = False
        
        if hand_width_ratio < 0.8:
            feedback_messages.append("손을 어깨 너비로 벌리세요")
            is_correct = False
        elif hand_width_ratio > 1.5:
            feedback_messages.append("손 간격이 너무 넓습니다")
            is_correct = False
        
        # Check elbow position (shouldn't flare too much)
        left_elbow_flare = abs(left_elbow[0] - left_shoulder[0]) / shoulder_width
        right_elbow_flare = abs(right_elbow[0] - right_shoulder[0]) / shoulder_width
        avg_elbow_flare = (left_elbow_flare + right_elbow_flare) / 2
        
        if avg_elbow_flare > 0.6 and avg_elbow_angle < 120:
            feedback_messages.append("팔꿈치를 몸에 가깝게 유지하세요")
            is_correct = False
        
        # 4. REP COUNTING - Improved state machine
        rep_quality = 1.0 if is_correct else max(0.3, 1.0 - (0.15 * len(feedback_messages)))
        
        # State transitions: up -> down -> up
        if avg_elbow_angle > 150 and self.exercise_state in ["ready", "down"]:
            self.exercise_state = "up"
        elif avg_elbow_angle < 90 and self.exercise_state == "up":
            self.exercise_state = "down"
            # Check if it was a good rep
            if rep_quality > 0.7:
                feedback_messages.append("좋은 자세로 내려왔습니다!")
        elif avg_elbow_angle > 140 and self.exercise_state == "down":
            # Complete rep
            self.exercise_state = "up"
            self.rep_count += 1
            self.check_completion()
            
            # Track form history
            self.form_history.append({
                'rep': self.rep_count,
                'quality': rep_quality,
                'errors': feedback_messages.copy()
            })
            
            if rep_quality > 0.8:
                feedback_messages.append(f"훌륭합니다! {self.rep_count}회 완료")
        
        # 5. DEPTH FEEDBACK
        if avg_elbow_angle > 110 and self.exercise_state == "down":
            feedback_messages.append("더 깊이 내려가세요 - 90도 목표")
            is_correct = False
        elif avg_elbow_angle < 70:
            feedback_messages.append("너무 깊이 내려갔습니다")
        
        return PostureFeedback(
            is_correct=is_correct,
            feedback_messages=feedback_messages if feedback_messages else ["완벽한 푸시업 자세입니다!"],
            angle_data={
                "elbow_angle": avg_elbow_angle,
                "body_alignment": body_alignment_angle,
                "hand_width_ratio": hand_width_ratio,
                "rep_count": self.rep_count,
                "exercise_state": self.exercise_state
            },
            confidence=min(landmarks[11].visibility, landmarks[13].visibility, 
                        landmarks[15].visibility, landmarks[23].visibility),
            rep_quality=rep_quality
        )
    
    def analyze_squat(self, landmarks) -> PostureFeedback:
        """Enhanced squat form analysis with proper biomechanics"""
        # Get key points
        left_shoulder = self.get_landmark_coordinates(landmarks, 11)
        right_shoulder = self.get_landmark_coordinates(landmarks, 12)
        left_hip = self.get_landmark_coordinates(landmarks, 23)
        right_hip = self.get_landmark_coordinates(landmarks, 24)
        left_knee = self.get_landmark_coordinates(landmarks, 25)
        right_knee = self.get_landmark_coordinates(landmarks, 26)
        left_ankle = self.get_landmark_coordinates(landmarks, 27)
        right_ankle = self.get_landmark_coordinates(landmarks, 28)
        
        feedback_messages = []
        is_correct = True
        
        # Calculate midpoints
        mid_shoulder = ((left_shoulder[0] + right_shoulder[0]) / 2, 
                    (left_shoulder[1] + right_shoulder[1]) / 2)
        mid_hip = ((left_hip[0] + right_hip[0]) / 2, 
                (left_hip[1] + right_hip[1]) / 2)
        mid_ankle = ((left_ankle[0] + right_ankle[0]) / 2, 
                    (left_ankle[1] + right_ankle[1]) / 2)
        
        # 1. POSITION VALIDATION - Must be standing
        if abs(mid_shoulder[1] - mid_hip[1]) < 0.25:
            return PostureFeedback(
                is_correct=False,
                feedback_messages=["일어서서 스쿼트를 준비하세요"],
                angle_data={"rep_count": self.rep_count},
                confidence=0.5,
                rep_quality=0.0
            )
        
        # 2. BIOMECHANICAL ANALYSIS
        # Calculate knee angles
        left_knee_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
        right_knee_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
        avg_knee_angle = (left_knee_angle + right_knee_angle) / 2
        
        # Hip hinge - hip should move back
        hip_to_ankle_distance = abs(mid_hip[0] - mid_ankle[0])
        body_height = abs(mid_shoulder[1] - mid_ankle[1])
        hip_hinge_ratio = hip_to_ankle_distance / (body_height + 0.01)
        
        # Knee tracking - knees shouldn't cave in
        knee_separation = abs(left_knee[0] - right_knee[0])
        ankle_separation = abs(left_ankle[0] - right_ankle[0])
        knee_tracking_ratio = knee_separation / (ankle_separation + 0.01)
        
        # 3. FORM ANALYSIS
        # Knee position relative to toes
        left_knee_forward = (left_knee[0] - left_ankle[0]) / body_height
        right_knee_forward = (right_knee[0] - right_ankle[0]) / body_height
        avg_knee_forward = (left_knee_forward + right_knee_forward) / 2
        
        if avg_knee_forward > 0.12:  # Proportional to body size
            feedback_messages.append("무릎이 너무 앞으로 나왔습니다 - 엉덩이를 뒤로")
            is_correct = False
        
        # Hip hinge check
        if hip_hinge_ratio < 0.05 and avg_knee_angle < 120:
            feedback_messages.append("엉덩이를 뒤로 빼면서 앉으세요")
            is_correct = False
        
        # Knee tracking
        if knee_tracking_ratio < 0.6:
            feedback_messages.append("무릎이 안으로 모이지 않게 하세요")
            is_correct = False
        
        # Back straightness
        torso_angle = self.calculate_angle(mid_shoulder, mid_hip, (mid_hip[0], mid_hip[1] + 0.1))
        if torso_angle < 70:  # Too bent forward
            feedback_messages.append("상체를 너무 앞으로 기울이지 마세요")
            is_correct = False
        
        # 4. DEPTH ANALYSIS
        # Calculate squat depth using hip and knee position
        standing_hip_height = 0.6  # Approximate standing hip height in normalized coordinates
        current_hip_height = mid_hip[1]
        squat_depth = (standing_hip_height - current_hip_height) / standing_hip_height
        
        # 5. REP COUNTING - Improved logic
        rep_quality = 1.0 if is_correct else max(0.4, 1.0 - (0.12 * len(feedback_messages)))
        
        # State machine: standing -> down -> standing
        if avg_knee_angle > 160 and self.exercise_state in ["ready", "down"]:
            self.exercise_state = "standing"
        elif avg_knee_angle < 110 and self.exercise_state == "standing":
            self.exercise_state = "down"
            if squat_depth > 0.15:  # Good depth
                feedback_messages.append("좋은 깊이입니다!")
        elif avg_knee_angle > 150 and self.exercise_state == "down":
            # Complete rep
            self.exercise_state = "standing"
            self.rep_count += 1
            self.check_completion()
            
            # Track form history
            self.form_history.append({
                'rep': self.rep_count,
                'quality': rep_quality,
                'errors': feedback_messages.copy()
            })
            
            if rep_quality > 0.8:
                feedback_messages.append(f"완벽한 스쿼트! {self.rep_count}회 완료")
        
        # 6. DEPTH FEEDBACK
        if avg_knee_angle > 120 and self.exercise_state == "down":
            feedback_messages.append("더 깊이 앉으세요 - 허벅지가 바닥과 평행하게")
            is_correct = False
        elif avg_knee_angle < 70:
            feedback_messages.append("너무 깊이 앉았습니다")
        
        return PostureFeedback(
            is_correct=is_correct,
            feedback_messages=feedback_messages if feedback_messages else ["완벽한 스쿼트 자세입니다!"],
            angle_data={
                "knee_angle": avg_knee_angle,
                "hip_hinge_ratio": hip_hinge_ratio,
                "knee_tracking_ratio": knee_tracking_ratio,
                "squat_depth": squat_depth,
                "rep_count": self.rep_count,
                "exercise_state": self.exercise_state
            },
            confidence=min(landmarks[23].visibility, landmarks[25].visibility, 
                        landmarks[27].visibility),
            rep_quality=rep_quality
        )
    
    def analyze_leg_raise(self, landmarks) -> PostureFeedback:
        """Enhanced leg raise analysis with core stability focus"""
        # Get key points
        left_shoulder = self.get_landmark_coordinates(landmarks, 11)
        right_shoulder = self.get_landmark_coordinates(landmarks, 12)
        left_hip = self.get_landmark_coordinates(landmarks, 23)
        right_hip = self.get_landmark_coordinates(landmarks, 24)
        left_knee = self.get_landmark_coordinates(landmarks, 25)
        right_knee = self.get_landmark_coordinates(landmarks, 26)
        left_ankle = self.get_landmark_coordinates(landmarks, 27)
        right_ankle = self.get_landmark_coordinates(landmarks, 28)
        
        feedback_messages = []
        is_correct = True
        
        # Calculate midpoints
        mid_shoulder = ((left_shoulder[0] + right_shoulder[0]) / 2, 
                    (left_shoulder[1] + right_shoulder[1]) / 2)
        mid_hip = ((left_hip[0] + right_hip[0]) / 2, 
                (left_hip[1] + right_hip[1]) / 2)
        mid_knee = ((left_knee[0] + right_knee[0]) / 2, 
                (left_knee[1] + right_knee[1]) / 2)
        mid_ankle = ((left_ankle[0] + right_ankle[0]) / 2, 
                    (left_ankle[1] + right_ankle[1]) / 2)
        
        # 1. POSITION VALIDATION - Must be lying down
        if abs(mid_shoulder[1] - mid_hip[1]) > 0.15:
            return PostureFeedback(
                is_correct=False,
                feedback_messages=["등을 바닥에 대고 누워서 레그레이즈를 준비하세요"],
                angle_data={"rep_count": self.rep_count},
                confidence=0.5,
                rep_quality=0.0
            )
        
        # 2. FORM ANALYSIS
        # Leg straightness
        left_leg_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
        right_leg_angle = self.calculate_angle(right_hip, right_knee, right_ankle)
        avg_leg_angle = (left_leg_angle + right_leg_angle) / 2
        
        if abs(avg_leg_angle - 180) > 25:
            feedback_messages.append("다리를 곧게 펴세요")
            is_correct = False
        
        # Leg elevation (how high legs are raised)
        leg_elevation = abs(mid_ankle[1] - mid_hip[1])
        
        # Lower back stability - hip position shouldn't change much
        baseline_hip_y = getattr(self, 'baseline_hip_y', mid_hip[1])
        if not hasattr(self, 'baseline_hip_y'):
            self.baseline_hip_y = mid_hip[1]
        
        hip_lift = abs(mid_hip[1] - baseline_hip_y)
        
        if hip_lift > 0.03:  # Hip lifting off ground
            feedback_messages.append("허리를 바닥에 붙이세요 - 엉덩이가 뜨지 않게")
            is_correct = False
        
        # Leg position symmetry
        leg_symmetry = abs(left_ankle[1] - right_ankle[1])
        if leg_symmetry > 0.05:
            feedback_messages.append("양쪽 다리를 같은 높이로 유지하세요")
            is_correct = False
        
        # 3. REP COUNTING - Based on leg elevation
        rep_quality = 1.0 if is_correct else max(0.4, 1.0 - (0.15 * len(feedback_messages)))
        
        # State machine: down -> up -> down
        if leg_elevation < 0.15 and self.exercise_state in ["ready", "up"]:
            self.exercise_state = "down"
        elif leg_elevation > 0.35 and self.exercise_state == "down":
            self.exercise_state = "up"
            if avg_leg_angle > 160:  # Good leg straightness
                feedback_messages.append("다리를 잘 올렸습니다!")
        elif leg_elevation < 0.1 and self.exercise_state == "up":
            # Complete rep
            self.exercise_state = "down"
            self.rep_count += 1
            self.check_completion()
            
            # Track form history
            self.form_history.append({
                'rep': self.rep_count,
                'quality': rep_quality,
                'errors': feedback_messages.copy()
            })
            
            if rep_quality > 0.8:
                feedback_messages.append(f"훌륭한 레그레이즈! {self.rep_count}회 완료")
        
        # 4. RANGE OF MOTION FEEDBACK
        if leg_elevation > 0.25 and leg_elevation < 0.4 and self.exercise_state == "up":
            feedback_messages.append("더 높이 올려보세요")
        elif leg_elevation > 0.5:
            feedback_messages.append("다리를 너무 높이 올렸습니다")
        
        return PostureFeedback(
            is_correct=is_correct,
            feedback_messages=feedback_messages if feedback_messages else ["완벽한 레그레이즈 자세입니다!"],
            angle_data={
                "leg_angle": avg_leg_angle,
                "leg_elevation": leg_elevation,
                "hip_stability": hip_lift,
                "leg_symmetry": leg_symmetry,
                "rep_count": self.rep_count,
                "exercise_state": self.exercise_state
            },
            confidence=min(landmarks[23].visibility, landmarks[27].visibility),
            rep_quality=rep_quality
        )
    
    def analyze_dumbbell_curl(self, landmarks) -> PostureFeedback:
        """Enhanced dumbbell curl analysis with robust rep counting and feedback"""
        # Get key points
        left_shoulder = self.get_landmark_coordinates(landmarks, 11)
        right_shoulder = self.get_landmark_coordinates(landmarks, 12)
        left_elbow = self.get_landmark_coordinates(landmarks, 13)
        right_elbow = self.get_landmark_coordinates(landmarks, 14)
        left_wrist = self.get_landmark_coordinates(landmarks, 15)
        right_wrist = self.get_landmark_coordinates(landmarks, 16)
        left_hip = self.get_landmark_coordinates(landmarks, 23)
        right_hip = self.get_landmark_coordinates(landmarks, 24)

        feedback_messages = []
        is_correct = True

        # Calculate midpoints
        mid_shoulder = ((left_shoulder[0] + right_shoulder[0]) / 2, 
                    (left_shoulder[1] + right_shoulder[1]) / 2)
        mid_hip = ((left_hip[0] + right_hip[0]) / 2, 
                (left_hip[1] + right_hip[1]) / 2)

        # 1. POSITION VALIDATION - Must be standing
        if abs(mid_shoulder[1] - mid_hip[1]) < 0.25:
            return PostureFeedback(
                is_correct=False,
                feedback_messages=["일어서서 덤벨컬을 준비하세요"],
                angle_data={"rep_count": self.rep_count},
                confidence=0.5,
                rep_quality=0.0
            )

        # 2. ARM ANALYSIS - Determine which arm is active
        left_elbow_angle = self.calculate_angle(left_shoulder, left_elbow, left_wrist)
        right_elbow_angle = self.calculate_angle(right_shoulder, right_elbow, right_wrist)

        # Detect active arm based on elbow flexion and wrist position
        left_curling = left_elbow_angle < 130 and left_wrist[1] < left_elbow[1]
        right_curling = right_elbow_angle < 130 and right_wrist[1] < right_elbow[1]

        # Determine active arm and metrics
        if left_curling and not right_curling:
            active_angle = left_elbow_angle
            active_side = "left"
            active_elbow = left_elbow
            active_shoulder = left_shoulder
            active_wrist = left_wrist
        elif right_curling and not left_curling:
            active_angle = right_elbow_angle
            active_side = "right"
            active_elbow = right_elbow
            active_shoulder = right_shoulder
            active_wrist = right_wrist
        elif left_curling and right_curling:
            # Both arms curling
            active_angle = min(left_elbow_angle, right_elbow_angle)
            active_side = "both"
            active_elbow = left_elbow if left_elbow_angle < right_elbow_angle else right_elbow
            active_shoulder = left_shoulder if left_elbow_angle < right_elbow_angle else right_shoulder
            active_wrist = left_wrist if left_elbow_angle < right_elbow_angle else right_wrist
        else:
            # Neither arm curling - use the more flexed one
            if left_elbow_angle < right_elbow_angle:
                active_angle = left_elbow_angle
                active_side = "left"
                active_elbow = left_elbow
                active_shoulder = left_shoulder
                active_wrist = left_wrist
            else:
                active_angle = right_elbow_angle
                active_side = "right"
                active_elbow = right_elbow
                active_shoulder = right_shoulder
                active_wrist = right_wrist

        # 3. FORM ANALYSIS
        # Elbow stability - elbow shouldn't move much
        shoulder_width = abs(left_shoulder[0] - right_shoulder[0])
        elbow_drift = abs(active_elbow[0] - active_shoulder[0]) / (shoulder_width + 0.01)

        if elbow_drift > 0.3:
            feedback_messages.append(f"{active_side} 팔꿈치를 몸에 고정하세요 - 흔들리지 않게")
            is_correct = False

        # Shoulder stability - shoulders shouldn't move
        if hasattr(self, 'baseline_shoulder_y'):
            shoulder_movement = abs(mid_shoulder[1] - self.baseline_shoulder_y)
            if shoulder_movement > 0.02:
                feedback_messages.append("어깨를 고정하세요 - 이두근만 사용")
                is_correct = False
        else:
            self.baseline_shoulder_y = mid_shoulder[1]

        # Body sway check
        if hasattr(self, 'baseline_hip_x'):
            body_sway = abs(mid_hip[0] - self.baseline_hip_x)
            if body_sway > 0.03:
                feedback_messages.append("몸을 흔들지 마세요 - 안정적으로")
                is_correct = False
        else:
            self.baseline_hip_x = mid_hip[0]

        # Wrist position - should be aligned
        wrist_elbow_alignment = abs(active_wrist[0] - active_elbow[0]) / shoulder_width
        if wrist_elbow_alignment > 0.2:
            feedback_messages.append("손목을 팔꿈치와 일직선으로")
            is_correct = False

        # 4. REP COUNTING (robust state machine)
        rep_quality = 1.0 if is_correct else max(0.4, 1.0 - (0.12 * len(feedback_messages)))

        # --- Rep Counting State Machine ---
        # States: "ready" (start), "extended" (arm down), "flexed" (arm up)
        # Only count rep when full flexion and then full extension is detected

        # Debug print for tuning
        # print(f"Angle: {active_angle:.1f}, State: {self.exercise_state}, Rep: {self.rep_count}")

        if not hasattr(self, 'exercise_state') or self.exercise_state not in ["ready", "extended", "flexed"]:
            self.exercise_state = "ready"

        # Transition to extended (arm down)
        if active_angle > 150 and self.exercise_state in ["ready", "flexed"]:
            self.exercise_state = "extended"
        # Transition to flexed (arm up)
        elif active_angle < 60 and self.exercise_state == "extended":
            self.exercise_state = "flexed"
            feedback_messages.append("좋은 수축입니다!")
        # Count rep: flexed → extended
        elif active_angle > 140 and self.exercise_state == "flexed":
            self.exercise_state = "extended"
            self.rep_count += 1
            self.check_completion()
            self.form_history.append({
                'rep': self.rep_count,
                'quality': rep_quality,
                'errors': feedback_messages.copy()
            })
            if rep_quality > 0.8:
                feedback_messages.append(f"완벽한 컬! {self.rep_count}회 완료")

        # 5. RANGE OF MOTION FEEDBACK
        if 90 < active_angle < 140 and self.exercise_state == "flexed":
            feedback_messages.append("더 높이 올려보세요")
        elif active_angle < 30:
            feedback_messages.append("너무 높이 올렸습니다")

        return PostureFeedback(
            is_correct=is_correct,
            feedback_messages=feedback_messages if feedback_messages else ["완벽한 덤벨컬 자세입니다!"],
            angle_data={
                "active_angle": active_angle,
                "active_side": active_side,
                "elbow_stability": elbow_drift,
                "rep_count": self.rep_count,
                "exercise_state": self.exercise_state
            },
            confidence=min(landmarks[11].visibility, landmarks[13].visibility, 
                        landmarks[15].visibility),
            rep_quality=rep_quality
        )
        
    def analyze_one_arm_row(self, landmarks) -> PostureFeedback:
        """Analyze one-arm dumbbell row form."""
        # Detect which arm is active based on elbow position
        left_elbow = self.get_landmark_coordinates(landmarks, 13)
        right_elbow = self.get_landmark_coordinates(landmarks, 14)
        left_wrist = self.get_landmark_coordinates(landmarks, 15)
        right_wrist = self.get_landmark_coordinates(landmarks, 16)
        left_shoulder = self.get_landmark_coordinates(landmarks, 11)
        right_shoulder = self.get_landmark_coordinates(landmarks, 12)
        left_hip = self.get_landmark_coordinates(landmarks, 23)
        right_hip = self.get_landmark_coordinates(landmarks, 24)
        
        feedback_messages = []
        is_correct = True
        
        # Check bent-over position
        mid_shoulder = ((left_shoulder[0] + right_shoulder[0]) / 2, 
                       (left_shoulder[1] + right_shoulder[1]) / 2)
        mid_hip = ((left_hip[0] + right_hip[0]) / 2, 
                  (left_hip[1] + right_hip[1]) / 2)
        
        # Check torso angle
        torso_angle = self.calculate_angle(
            (mid_shoulder[0], mid_shoulder[1] - 0.2),
            mid_shoulder,
            mid_hip
        )
        
        if torso_angle < 45 or torso_angle > 135:
            return PostureFeedback(
                is_correct=False,
                feedback_messages=["Bend forward at the hips - back parallel to ground"],
                angle_data={"rep_count": self.rep_count},
                confidence=0.5,
                rep_quality=0.0
            )
        
        # Determine active arm (higher elbow Y position = rowing)
        if left_elbow[1] < right_elbow[1]:
            active_shoulder, active_elbow, active_wrist = left_shoulder, left_elbow, left_wrist
            side = "left"
        else:
            active_shoulder, active_elbow, active_wrist = right_shoulder, right_elbow, right_wrist
            side = "right"
        
        # Calculate elbow angle
        elbow_angle = self.calculate_angle(active_shoulder, active_elbow, active_wrist)
        
        # Check velocity
        if not self.check_movement_speed(elbow_angle, 'row_elbow'):
            return PostureFeedback(
                is_correct=False,
                feedback_messages=["Control your rowing speed"],
                angle_data={"elbow_angle": elbow_angle, "rep_count": self.rep_count},
                confidence=0.7,
                rep_quality=0.5
            )
        
        # Back should be relatively parallel to ground
        back_angle = abs(mid_shoulder[1] - mid_hip[1])
        if back_angle > 0.3:
            feedback_messages.append("Keep your back flat and parallel to ground")
            is_correct = False
        
        # Check elbow position at top
        if elbow_angle < 120 and active_elbow[1] < active_shoulder[1]:
            feedback_messages.append("Good elbow position at top")
        elif active_elbow[1] > active_shoulder[1]:
            feedback_messages.append("Pull elbow higher - lead with elbow, not wrist")
            is_correct = False
        
        # Calculate rep quality
        rep_quality = 1.0 if is_correct else max(0.5, 1.0 - (0.1 * len(feedback_messages)))
        
        # Track rep state
        if active_elbow[1] < active_shoulder[1] and self.exercise_state == "ready":
            self.exercise_state = "up"
        elif active_elbow[1] > active_shoulder[1] + 0.1 and self.exercise_state == "up":
            self.exercise_state = "ready"
            self.rep_count += 1
            self.check_completion()
            # Track form history
            self.form_history.append({
                'rep': self.rep_count,
                'quality': rep_quality,
                'errors': feedback_messages.copy()
            })
        
        # FIXED: Confidence calculation
        return PostureFeedback(
            is_correct=is_correct,
            feedback_messages=feedback_messages if feedback_messages else ["Form looks good!"],
            angle_data={
                "elbow_angle": elbow_angle,
                "active_side": side,
                "rep_count": self.rep_count
            },
            confidence=min(landmarks[11 if side == "left" else 12].visibility,
                         landmarks[13 if side == "left" else 14].visibility),
            rep_quality=rep_quality
        )
    
    def analyze_plank(self, landmarks) -> PostureFeedback:
        """Analyze plank with position validation and duration tracking."""
        self.log_analysis_step("플랭크 분석 시작")
        
        # Get key points
        nose = self.get_landmark_coordinates(landmarks, 0)
        left_shoulder = self.get_landmark_coordinates(landmarks, 11)
        right_shoulder = self.get_landmark_coordinates(landmarks, 12)
        left_elbow = self.get_landmark_coordinates(landmarks, 13)
        right_elbow = self.get_landmark_coordinates(landmarks, 14)
        left_hip = self.get_landmark_coordinates(landmarks, 23)
        right_hip = self.get_landmark_coordinates(landmarks, 24)
        left_ankle = self.get_landmark_coordinates(landmarks, 27)
        right_ankle = self.get_landmark_coordinates(landmarks, 28)

        feedback_messages = []
        is_correct = True

        # Calculate midpoints
        mid_shoulder = ((left_shoulder[0] + right_shoulder[0]) / 2, 
                    (left_shoulder[1] + right_shoulder[1]) / 2)
        mid_hip = ((left_hip[0] + right_hip[0]) / 2, 
                (left_hip[1] + right_hip[1]) / 2)
        mid_ankle = ((left_ankle[0] + right_ankle[0]) / 2, 
                    (left_ankle[1] + right_ankle[1]) / 2)
        mid_elbow = ((left_elbow[0] + right_elbow[0]) / 2,
                    (left_elbow[1] + right_elbow[1]) / 2)

        self.log_analysis_step("좌표 계산 완료", {
            "mid_shoulder": mid_shoulder,
            "mid_hip": mid_hip,
            "mid_ankle": mid_ankle
        })

        # 1. 포지션 체크 (어깨-엉덩이 수평)
        if not self.is_horizontal_position(mid_shoulder[1], mid_hip[1], threshold=0.15):
            self.log_analysis_step("수평 위치 아님")
            return PostureFeedback(
                is_correct=False,
                feedback_messages=["플랭크 자세를 취하세요 - 몸을 수평으로"],
                angle_data={"hold_time": 0, "rep_count": self.rep_count},
                confidence=0.5,
                rep_quality=0.0
            )

        # 2. 팔꿈치 위치로 플랭크 타입 판별
        elbow_shoulder_dist = abs(mid_elbow[1] - mid_shoulder[1])
        is_forearm_plank = elbow_shoulder_dist > 0.15

        self.log_analysis_step("플랭크 타입 판별", {
            "elbow_shoulder_dist": elbow_shoulder_dist,
            "is_forearm_plank": is_forearm_plank
        })

        # 3. 몸 일직선 판정
        body_alignment_angle = self.calculate_angle(mid_shoulder, mid_hip, mid_ankle)
        if abs(body_alignment_angle - 180) > 20:
            if body_alignment_angle < 160:
                feedback_messages.append("엉덩이를 올리세요 - 일직선 유지")
                is_correct = False
            elif body_alignment_angle > 200:
                feedback_messages.append("엉덩이를 내리세요 - 처지지 않게")
                is_correct = False

        # 4. 머리 위치 체크
        spine_vector = (mid_hip[0] - mid_shoulder[0], mid_hip[1] - mid_shoulder[1])
        expected_head_x = mid_shoulder[0] + 0.2 * spine_vector[0]
        head_alignment = abs(nose[0] - expected_head_x)
        
        if head_alignment > 0.1:
            feedback_messages.append("머리를 척추와 중립으로 유지하세요")
            is_correct = False

        # 5. 어깨 너비 체크 (전완 플랭크)
        shoulder_width = abs(left_shoulder[0] - right_shoulder[0])
        if is_forearm_plank and shoulder_width < 0.15:
            feedback_messages.append("어깨가 모이지 않게 하세요")
            is_correct = False

        # 6. 상태 관리
        if is_correct and self.exercise_state != "holding":
            self.exercise_state = "holding"
            if not self.exercise_start_time:
                import time
                self.exercise_start_time = time.time()
        elif not is_correct and self.exercise_state == "holding":
            self.exercise_state = "ready"
            self.exercise_start_time = None

        # 7. 시간 계산
        current_hold_time = 0
        if self.exercise_start_time:
            import time
            current_hold_time = time.time() - self.exercise_start_time

        self.log_analysis_step("플랭크 분석 완료", {
            "body_alignment_angle": body_alignment_angle,
            "head_alignment": head_alignment,
            "shoulder_width": shoulder_width,
            "is_correct": is_correct,
            "hold_time": current_hold_time
        })

        return PostureFeedback(
            is_correct=is_correct,
            feedback_messages=feedback_messages if feedback_messages else ["훌륭한 플랭크 자세! 계속 유지하세요!"],
            angle_data={
                "body_alignment": body_alignment_angle,
                "plank_type": "forearm" if is_forearm_plank else "high",
                "hold_time": current_hold_time,
                "rep_count": self.rep_count
            },
            confidence=self.get_landmark_visibility(landmarks, [11, 23, 27]),
            rep_quality=1.0 if is_correct else 0.5
        )
    
    def reset_exercise_state(self):
        """Reset exercise tracking state."""
        self.rep_count = 0
        self.exercise_state = "ready"
        self.prev_landmarks = None
        self.target_reps = None
        self.on_exercise_complete = None
        self.prev_angles = {}
        self.angle_history = []
        self.exercise_start_time = None
        self.hold_duration = 0
        self.form_history = []
    
    def get_form_summary(self) -> Dict:
        """Get summary of form quality throughout the workout."""
        if not self.form_history:
            return {"average_quality": 1.0, "total_reps": 0, "common_errors": []}
        
        # Calculate average quality
        total_quality = sum(entry.get('quality', 1.0) for entry in self.form_history)
        avg_quality = total_quality / len(self.form_history)
        
        # Find common errors
        all_errors = []
        for entry in self.form_history:
            all_errors.extend(entry.get('errors', []))
        
        # Count error frequency
        error_counts = {}
        for error in all_errors:
            error_counts[error] = error_counts.get(error, 0) + 1
        
        # Sort by frequency
        common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "average_quality": avg_quality,
            "total_reps": self.rep_count,
            "common_errors": [error[0] for error in common_errors],
            "form_history": self.form_history
        }
    
    def is_horizontal_position(self, shoulder_y: float, hip_y: float, threshold: float = 0.15) -> bool:
        """
        Check if body is in horizontal position (for pushup, plank, etc.)
        
        Args:
            shoulder_y: Y coordinate of shoulder midpoint
            hip_y: Y coordinate of hip midpoint  
            threshold: Maximum allowed vertical difference
        
        Returns:
            bool: True if body is horizontal
        """
        return abs(shoulder_y - hip_y) <= threshold
    
    def get_landmark_visibility(self, landmarks, indices: list) -> float:
        """
        Get minimum visibility score for given landmark indices
        
        Args:
            landmarks: MediaPipe landmarks
            indices: List of landmark indices to check
            
        Returns:
            float: Minimum visibility score
        """
        if not landmarks or len(landmarks) <= max(indices):
            return 0.0
        
        visibilities = []
        for idx in indices:
            if hasattr(landmarks[idx], 'visibility'):
                visibilities.append(landmarks[idx].visibility)
            else:
                visibilities.append(1.0)  # Default if no visibility info
        
        return min(visibilities) if visibilities else 0.0

    def calculate_distance(self, point1: tuple, point2: tuple) -> float:
        """
        Calculate Euclidean distance between two points
        
        Args:
            point1: (x, y) coordinates
            point2: (x, y) coordinates
            
        Returns:
            float: Distance between points
        """
        import math
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def get_body_orientation(self, landmarks) -> str:
        """
        Determine body orientation (front, side, back)
        
        Args:
            landmarks: MediaPipe pose landmarks
            
        Returns:
            str: 'front', 'side', or 'back'
        """
        # Use shoulder and hip visibility to determine orientation
        left_shoulder_vis = landmarks[11].visibility if hasattr(landmarks[11], 'visibility') else 1.0
        right_shoulder_vis = landmarks[12].visibility if hasattr(landmarks[12], 'visibility') else 1.0
        
        # If one shoulder is much less visible, person is likely sideways
        shoulder_vis_diff = abs(left_shoulder_vis - right_shoulder_vis)
        
        if shoulder_vis_diff > 0.3:
            return 'side'
        elif min(left_shoulder_vis, right_shoulder_vis) < 0.5:
            return 'back'
        else:
            return 'front'

    def log_analysis_step(self, step: str, data: dict = None):
        """
        Log analysis steps for debugging
        
        Args:
            step: Description of the analysis step
            data: Optional data to log
        """
        import time
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {step}")
        if data:
            for key, value in data.items():
                print(f"  {key}: {value}")

    def convert_websocket_landmarks(self, landmarks_data: List[Dict]) -> List:
        """Convert WebSocket landmark format to internal landmark objects"""
        try:
            converted_landmarks = []
            for landmark_dict in landmarks_data:
                # Use SimpleNamespace for dynamic attribute assignment
                landmark_obj = SimpleNamespace(
                    x=float(landmark_dict.get('x', 0)),
                    y=float(landmark_dict.get('y', 0)),
                    z=float(landmark_dict.get('z', 0)),
                    visibility=float(landmark_dict.get('visibility', 1.0))
                )
                converted_landmarks.append(landmark_obj)
            return converted_landmarks
        except Exception as e:
            print(f"Error converting landmarks: {str(e)}")
            return []

    def analyze_landmarks_directly(self, landmarks_data: List[Dict], exercise: Exercise) -> Optional[PostureFeedback]:
        """Analyze exercise form directly from landmark data (no frame conversion needed)"""
        
        try:
            # Convert landmark format
            landmarks = self.convert_websocket_landmarks(landmarks_data)
            
            if len(landmarks) < 33:
                print(f"Insufficient landmarks: {len(landmarks)}/33")
                return None
            
            # Apply smoothing
            if self.prev_landmarks is not None:
                landmarks = self.smooth_landmarks(landmarks, self.prev_landmarks, self.alpha)
            self.prev_landmarks = landmarks
            
            # Perform exercise-specific analysis (same logic as before)
            if exercise == Exercise.PUSHUP:
                return self.analyze_pushup(landmarks)
            elif exercise == Exercise.SQUAT:
                return self.analyze_squat(landmarks)
            elif exercise == Exercise.LEG_RAISE:
                return self.analyze_leg_raise(landmarks)
            elif exercise == Exercise.DUMBBELL_CURL:
                return self.analyze_dumbbell_curl(landmarks)
            elif exercise == Exercise.ONE_ARM_ROW:
                return self.analyze_one_arm_row(landmarks)
            elif exercise == Exercise.PLANK:
                return self.analyze_plank(landmarks)
            else:
                print(f"Unknown exercise type: {exercise}")
                return None
                
        except Exception as e:
            print(f"Error in direct landmark analysis: {str(e)}")
            return None

# Example usage with routine integration
def process_exercise_with_routine(video_source, exercise: Exercise, target_reps: int):
    """
    Process exercise with target reps from routine.
    
    Args:
        video_source: Can be video path (str) or camera index (int)
        exercise: Exercise type
        target_reps: Target number of reps from routine
    
    Returns:
        bool: True if completed successfully
    """
    analyzer = ExerciseAnalyzer()
    
    # Show camera setup instructions
    print(f"\nCamera Setup: {analyzer.get_camera_instructions(exercise)}")
    print("Press any key when ready...")
    
    # Set target reps
    completed = False
    def on_complete():
        nonlocal completed
        completed = True
        print(f"\n✓ Exercise complete! Reached {target_reps} reps!")
    
    analyzer.set_target_reps(target_reps, on_complete)
    
    # Open video source
    cap = cv2.VideoCapture(video_source)
    
    print(f"Starting {exercise.value} - Target: {target_reps} reps")
    print("Press 'q' to quit early")
    
    frame_count = 0
    while cap.isOpened() and not completed:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Resize for consistent processing
        frame = cv2.resize(frame, (640, 480))
        
        # Skip frames for performance
        frame_count += 1
        if frame_count % 2 != 0:
            continue
        
        # Analyze exercise
        feedback = analyzer.analyze_exercise(frame, exercise)
        
        # Draw annotated frame
        annotated_frame = analyzer.draw_landmarks(frame, include_feedback=True, feedback=feedback)
        
        # Display
        cv2.imshow(f'{exercise.value} Analysis', annotated_frame)
        
        # Check for early quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nExercise terminated early")
            break
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    
    # Show form summary
    summary = analyzer.get_form_summary()
    print(f"\nForm Summary:")
    print(f"Average Quality: {summary['average_quality']:.0%}")
    print(f"Total Reps: {summary['total_reps']}")
    if summary['common_errors']:
        print(f"Common Errors: {', '.join(summary['common_errors'])}")
    
    return completed
