// frontend/src/services/workoutService.js - FIXED VERSION

const API_BASE_URL = process.env.REACT_APP_CV_SERVICE_URL || 'http://192.168.0.29:8001';

class WorkoutService {
  // Helper method for error handling
  async handleResponse(response, operation = 'API operation') {
    if (!response.ok) {
      let errorMessage = `Failed to ${operation}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch (e) {
        // If we can't parse the error response, use the default message
        errorMessage = `${errorMessage} (${response.status}: ${response.statusText})`;
      }
      throw new Error(errorMessage);
    }
    return await response.json();
  }

  async getAllRoutines(userId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/workout/routines?user_id=${userId}`);
      return await this.handleResponse(response, 'fetch routines');
    } catch (error) {
      console.error('Error fetching routines:', error);
      throw error;
    }
  }

  async getRoutineByDay(userId, day) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/workout/routines/${day}?user_id=${userId}`);
      return await this.handleResponse(response, `fetch routine for day ${day}`);
    } catch (error) {
      console.error('Error fetching routine:', error);
      throw error;
    }
  }

  async resetUserRoutines(userId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/workout/routines/user/${userId}/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      return await this.handleResponse(response, 'reset routines');
    } catch (error) {
      console.error('Error resetting routines:', error);
      throw error;
    }
  }

  async completeRoutine(day, userId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/workout/routines/${day}/complete?user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      return await this.handleResponse(response, 'complete routine');
    } catch (error) {
      console.error('Error completing routine:', error);
      throw error;
    }
  }

  // FIXED: Use PUT method for updating sets (matches backend)
  async updateSet(day, exerciseId, setId, updateData, userId) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/workout/routines/${day}/exercises/${exerciseId}/sets/${setId}?user_id=${userId}`,
        {
          method: 'PUT', // Changed from POST to PUT
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updateData)
        }
      );
      return await this.handleResponse(response, 'update set');
    } catch (error) {
      console.error('Error updating set:', error);
      throw error;
    }
  }

  async addSet(day, exerciseId, userId) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/workout/routines/${day}/exercises/${exerciseId}/sets?user_id=${userId}`,
        { 
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }
      );
      return await this.handleResponse(response, 'add set');
    } catch (error) {
      console.error('Error adding set:', error);
      throw error;
    }
  }

  async deleteSet(day, exerciseId, setId, userId) {
    try {
      // const response = await fetch(
      //   `${API_BASE_URL}/api/workout/routines/${day}/exercises/${exerciseId}/sets/${setId}?user_id=${userId}`,
      //   { method: 'DELETE' }
      // );
      // return await this.handleResponse(response, 'delete set');
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
      return await this.handleResponse(response, 'delete exercise');
    } catch (error) {
      console.error('Error deleting exercise:', error);
      throw error;
    }
  }

  // FIXED: Enhanced toggle completion with better error handling
  async toggleSetCompletion(day, exerciseId, setId, userId) {
    try {
      console.log(`Toggling completion: day=${day}, exerciseId=${exerciseId}, setId=${setId}, userId=${userId}`);
      
      const response = await fetch(
        `${API_BASE_URL}/api/workout/routines/${day}/exercises/${exerciseId}/complete-set/${setId}?user_id=${userId}`,
        { 
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }
      );
      
      const result = await this.handleResponse(response, 'toggle set completion');
      console.log('Toggle result:', result);
      return result;
    } catch (error) {
      console.error('Error toggling set completion:', error);
      throw error;
    }
  }

  // NEW: Method specifically for marking sets complete from camera analysis
  async markSetCompleteFromCamera(day, exerciseId, setId, userId) {
    try {
      console.log(`Marking set complete from camera: day=${day}, exerciseId=${exerciseId}, setId=${setId}, userId=${userId}`);
      
      // First check if the set is already completed
      const routine = await this.getRoutineByDay(userId, day);
      const exercise = routine.exercises.find(ex => ex.id === exerciseId);
      if (!exercise) {
        throw new Error(`Exercise ${exerciseId} not found`);
      }
      
      const set = exercise.sets.find(s => s.id === setId);
      if (!set) {
        throw new Error(`Set ${setId} not found`);
      }
      
      // If already completed, don't toggle
      if (set.completed) {
        console.log('Set already completed, skipping...');
        return { message: 'Set already completed', completed: true };
      }
      
      // Mark as complete
      return await this.toggleSetCompletion(day, exerciseId, setId, userId);
    } catch (error) {
      console.error('Error marking set complete from camera:', error);
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
      return await this.handleResponse(response, 'trigger posture analysis');
    } catch (error) {
      console.error('Error triggering posture analysis:', error);
      throw error;
    }
  }

  // DEPRECATED: Remove this method as it doesn't exist in backend
  // async markExerciseComplete(day, exerciseName, userId) {
  //   // This method was calling a non-existent endpoint
  // }

  // NEW: Health check method
  async checkHealth() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/workout/ws/health`);
      return await this.handleResponse(response, 'check health');
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }

  // NEW: Test database connection
  async testConnection() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/workout/test-connection`);
      return await this.handleResponse(response, 'test connection');
    } catch (error) {
      console.error('Connection test failed:', error);
      throw error;
    }
  }
}

export default new WorkoutService();