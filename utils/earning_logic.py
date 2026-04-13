"""
Gamification earning logic - calculates rewards based on various multipliers and bonuses.
Handles submission bonuses, speedrun multipliers, academic weapon bonuses, and first blood bounties.
"""

from datetime import datetime
from typing import Dict, Tuple, Optional
from utils import gamification_db

class RewardCalculator:
    """Calculates Canvas Credits and XP rewards based on student performance."""
    
    # Base rewards
    SUBMISSION_BONUS_CC = 50
    ACADEMIC_WEAPON_CC = 100
    ACADEMIC_WEAPON_XP = 200
    FIRST_BLOOD_CC = 75
    GRADE_BONUS_MULTIPLIER = 5  # Total grades * 5
    
    # Speedrun multipliers
    SPEEDRUN_THRESHOLDS = [
        (36, 3.0),    # > 36 hours before due_date = 3x
        (24, 2.0),    # > 24 hours before due_date = 2x
        (12, 1.5),    # > 12 hours before due_date = 1.5x
    ]
    
    @staticmethod
    def calculate_submission_reward(
        submitted_at: datetime,
        due_at: Optional[datetime],
        grade: Optional[float] = None,
        is_first_submission: bool = False
    ) -> Tuple[int, int]:
        """
        Calculate CC and XP for a submission.
        
        Returns: (cc_earned, xp_earned)
        """
        cc_earned = RewardCalculator.SUBMISSION_BONUS_CC
        xp_earned = 0
        
        # Apply speedrun multiplier if we have due date
        if due_at and submitted_at:
            hours_before_due = (due_at - submitted_at).total_seconds() / 3600
            
            for threshold_hours, multiplier in RewardCalculator.SPEEDRUN_THRESHOLDS:
                if hours_before_due > threshold_hours:
                    cc_earned = int(cc_earned * multiplier)
                    break
        
        # Apply academic weapon bonus for high grades
        if grade is not None and grade >= 90:
            cc_earned += RewardCalculator.ACADEMIC_WEAPON_CC
            xp_earned += RewardCalculator.ACADEMIC_WEAPON_XP
        
        # Apply first blood bounty
        if is_first_submission:
            cc_earned += RewardCalculator.FIRST_BLOOD_CC
        
        # Minimum XP per submission (proportional to CC, roughly 1 XP per 2 CC)
        if xp_earned == 0:
            xp_earned = int(cc_earned / 2)
        else:
            xp_earned += int(cc_earned / 2)
        
        return (cc_earned, xp_earned)
    
    @staticmethod
    def calculate_starting_bonus(total_grade: float) -> Tuple[int, int]:
        """
        Calculate starting CC and XP bonus based on total grades.
        
        Formula: (average_grade * 5) for CC, doubled for XP
        """
        cc_bonus = int(total_grade * RewardCalculator.GRADE_BONUS_MULTIPLIER)
        xp_bonus = cc_bonus * 2
        
        return (cc_bonus, xp_bonus)
    
    @staticmethod
    def get_reward_summary(cc: int, xp: int) -> str:
        """Get human-readable reward summary."""
        return f"+{cc} CC | +{xp} XP"


class SubmissionProcessor:
    """Processes submissions from Canvas and awards appropriate rewards."""
    
    @staticmethod
    async def process_submission(
        user_id: int,
        submission: Dict,
        user_total_grade: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Process a single submission and award rewards if not already processed.
        
        Args:
            user_id: Discord user ID
            submission: Canvas submission object
            user_total_grade: User's total grade in course (for starting bonus)
        
        Returns: Reward dict {'cc': int, 'xp': int, 'reason': str} or None if already processed
        """
        submission_id = submission.get("id")
        
        # Check if already processed
        if gamification_db.is_submission_processed(user_id, submission_id):
            return None
        
        submitted_at_str = submission.get("submitted_at")
        due_at_str = submission.get("due_at")
        score = submission.get("score")
        grade = submission.get("grade")
        
        # Parse dates
        submitted_at = datetime.fromisoformat(submitted_at_str.replace("Z", "+00:00")) if submitted_at_str else None
        due_at = datetime.fromisoformat(due_at_str.replace("Z", "+00:00")) if due_at_str else None
        
        if not submitted_at:
            return None
        
        # Check if this is first submission of this assignment
        is_first = gamification_db.get_first_submission_user(submission_id) is None
        
        # Calculate grade from score if available
        grade_percent = None
        if score is not None and submission.get("points_possible"):
            grade_percent = (score / submission.get("points_possible")) * 100
        
        # Calculate reward
        cc_earned, xp_earned = RewardCalculator.calculate_submission_reward(
            submitted_at=submitted_at,
            due_at=due_at,
            grade=grade_percent,
            is_first_submission=is_first
        )
        
        # Build reason string
        reasons = [f"Submission bonus"]
        
        if grade_percent and grade_percent >= 90:
            reasons.append(f"Academic Weapon (Grade: {grade_percent:.1f}%)")
        
        if due_at and submitted_at:
            hours_before = (due_at - submitted_at).total_seconds() / 3600
            if hours_before > 36:
                reasons.append("Speedrun 3x (36+ hours early)")
            elif hours_before > 24:
                reasons.append("Speedrun 2x (24+ hours early)")
            elif hours_before > 12:
                reasons.append("Speedrun 1.5x (12+ hours early)")
        
        if is_first:
            reasons.append("First Blood bounty!")
        
        reward = {
            "cc": cc_earned,
            "xp": xp_earned,
            "reason": " | ".join(reasons),
            "assignment_id": submission.get("assignment_id"),
            "submission_id": submission_id
        }
        
        # Mark as processed
        gamification_db.mark_submission_processed(user_id, submission_id, reward)
        
        return reward


class LevelCalculator:
    """Handles level calculations and XP thresholds."""
    
    XP_PER_LEVEL = 100  # Each level requires 100 XP
    
    @staticmethod
    def get_level_from_xp(total_xp: int) -> int:
        """Calculate level from total XP."""
        return 1 + (total_xp // LevelCalculator.XP_PER_LEVEL)
    
    @staticmethod
    def get_xp_for_level(level: int) -> int:
        """Get total XP required to reach a specific level."""
        return (level - 1) * LevelCalculator.XP_PER_LEVEL
    
    @staticmethod
    def get_xp_to_next_level(total_xp: int) -> int:
        """Get XP needed to reach next level."""
        current_level = LevelCalculator.get_level_from_xp(total_xp)
        next_level_xp = LevelCalculator.get_xp_for_level(current_level + 1)
        return max(0, next_level_xp - total_xp)
    
    @staticmethod
    def get_progress_to_next_level(total_xp: int) -> float:
        """Get progress percentage (0-1) toward next level."""
        current_xp_for_level = LevelCalculator.get_xp_for_level(
            LevelCalculator.get_level_from_xp(total_xp)
        )
        xp_in_current_level = total_xp - current_xp_for_level
        return xp_in_current_level / LevelCalculator.XP_PER_LEVEL
