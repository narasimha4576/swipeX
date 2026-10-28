import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("swipex_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function errorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const names = {
      current_ctc_lpa: "Current CTC",
      expected_ctc_lpa: "Expected CTC",
      notice_period_days: "Notice period",
      graduation_year: "Graduation year",
      phone: "Phone",
      linkedin_url: "LinkedIn link",
      github_url: "GitHub link",
      portfolio_url: "Portfolio link",
      cover_letter: "Cover letter",
      experience_years: "Experience",
      salary_min_lpa: "Minimum salary",
      salary_max_lpa: "Maximum salary",
    };
    return detail
      .map((d) => {
        const field = names[d.loc[d.loc.length - 1]];
        const message = d.msg.replace("Value error, ", "");
        return field ? `${field}: ${message}` : message;
      })
      .join(". ");
  }
  return "Something went wrong. Is the backend running?";
}

export default api;