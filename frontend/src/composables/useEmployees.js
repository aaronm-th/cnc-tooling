import { ref } from 'vue'
import axios from 'axios'

export function useEmployees() {
  const employees = ref([])
  const isLoading = ref(false)

  const fetchEmployees = async (isPublic = false) => {
    isLoading.value = true
    try {
      // Wähle den Endpunkt basierend darauf, ob wir eingeloggt sind oder nicht
      const endpoint = isPublic ? '/api/terminal/users/' : '/api/users/all/'
      const config = {}

      if (!isPublic) {
        const token = localStorage.getItem('access_token')
        config.headers = { 'Authorization': `Bearer ${token}` }
      }

      const response = await axios.get(`${import.meta.env.VITE_API_URL}${endpoint}`, config)
      
      employees.value = response.data.map(member => ({
        id: member.id,
        name: `${member.first_name} ${member.last_name}`,
        status: member.status || 'Inactive',
        avatar: member.avatar,
        initials: (member.first_name?.[0] || '') + (member.last_name?.[0] || '')
      }))
    } catch (error) {
      console.error("Mitarbeiter-Ladefehler:", error)
    } finally {
      isLoading.value = false
    }
  }

  const toggleEmployeeStatus = async (employeeId) => {
    try {
      // Terminal is public, so we don't send a Bearer token here
      const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/terminal/toggle/`, {
        employee_id: employeeId
      });
      return response.data; // Should return { new_status: 'Checked In' }
    } catch (error) {
      console.error("Toggle failed:", error);
      throw error;
    }
  }


  return { employees, isLoading, fetchEmployees, toggleEmployeeStatus }
}