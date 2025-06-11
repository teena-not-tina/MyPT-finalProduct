// frontend/src/services/workoutService.js

const API_BASE_URL = process.env.REACT_APP_CV_SERVICE_URL || 'http://192.168.0.29:8001';

class WorkoutService {
  async getAllRoutines(userId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/workout/routines?user_id=${userId}`);
      if (!response.ok) throw new Error('Failed to fetch routines');
      return await response.json();
    } catch (error) {
      console.error('Error fetching routines:', error);
      throw error;
    }
  }

  async getRoutineByDay(userId, day) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/workout/routines/${day}?user_id=${userId}`);
      if (!response.ok) throw new Error(`Failed to fetch routine for day ${day}`);
      return await response.json();
    } catch (error) {
      console.error('Error fetching routine:', error);
      throw error;
    }
  }

  async resetUserRoutines(userId) {
    const response = await fetch(`${API_BASE_URL}/api/workout/routines/user/${userId}/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!response.ok) throw new Error('Failed to reset routines');
    return await response.json();
  }

  async completeRoutine(day, userId) {
    const response = await fetch(`${API_BASE_URL}/api/workout/routines/${day}/complete?user_id=${userId}`, {
      method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to complete routine');
    return await response.json();
  }

  async updateSet(day, exerciseId, setId, updateData, userId) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/workout/routines/${day}/exercises/${exerciseId}/sets/${setId}?user_id=${userId}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updateData)
        }
      );
      if (!response.ok) throw new Error('Failed to update set');
      return await response.json();
    } catch (error) {
      console.error('Error updating set:', error);
      throw error;
    }
  }

  async addSet(day, exerciseId, userId) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/workout/routines/${day}/exercises/${exerciseId}/sets?user_id=${userId}`,
        { method: 'POST' }
      );
      if (!response.ok) throw new Error('Failed to add set');
      return await response.json();
    } catch (error) {
      console.error('Error adding set:', error);
      throw error;
    }
  }

  async deleteSet(day, exerciseId, setId, userId) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/workout/routines/${day}/exercises/${exerciseId}/sets/${setId}?user_id=${userId}`,
        { method: 'DELETE' }
      );
      if (!response.ok) throw new Error('Failed to delete set');
      return await response.json();
    } catch (error) {
      console.error('Error deleting set:', error);
      throw error;
    }
  }

  async deleteExercise(day, exerciseId, userId) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/workout/routines/${day}/exercises/${exerciseId}?user_id=${userId}`,
        { method: 'DELETE' }
      );
      if (!response.ok) throw new Error('Failed to delete exercise');
      return await response.json();
    } catch (error) {
      console.error('Error deleting exercise:', error);
      throw error;
    }
  }

  async toggleSetCompletion(day, exerciseId, setId, userId) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/workout/routines/${day}/exercises/${exerciseId}/complete-set/${setId}?user_id=${userId}`,
        { method: 'POST' }
      );
      if (!response.ok) throw new Error('Failed to toggle set completion');
      return await response.json();
    } catch (error) {
      console.error('Error toggling set completion:', error);
      throw error;
    }
  }

  async triggerPostureAnalysis(exerciseName) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/workout/routines/camera/analyze`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ exercise_name: exerciseName })
        }
      );
      if (!response.ok) throw new Error('Failed to trigger posture analysis');
      return await response.json();
    } catch (error) {
      console.error('Error triggering posture analysis:', error);
      throw error;
    }
  }

  async markExerciseComplete(day, exerciseName, userId) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/workout/routines/${day}/exercises/complete`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            exercise_name: exerciseName,
            user_id: userId 
          })
        }
      );
      if (!response.ok) throw new Error('Failed to mark exercise complete');
      return await response.json();
    } catch (error) {
      console.error('Error marking exercise complete:', error);
      throw error;
    }
  }
}

export default new WorkoutService();