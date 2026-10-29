export const TYPE_LABEL = { mnc: "MNC", startup: "Startup", new_startup: "New startup", other: "Company" };
export const JOB_TYPE_LABEL = {
  full_time: "Full-time",
  internship: "Internship",
  apprenticeship: "Apprenticeship",
  part_time: "Part-time",
  contract: "Contract",
};
export const LEVEL_LABEL = { fresher: "Fresher", junior: "Junior", mid: "Mid-level", senior: "Senior" };
export const COMP_LABEL = {
  low: "Low competition",
  medium: "Medium competition",
  high: "High competition",
  unknown: "Competition unknown",
};

const GRADIENTS = [
  "linear-gradient(135deg, #0a84ff, #5e5ce6)",
  "linear-gradient(135deg, #ff375f, #ff9f0a)",
  "linear-gradient(135deg, #30d158, #0a84ff)",
  "linear-gradient(135deg, #bf5af2, #ff375f)",
  "linear-gradient(135deg, #ff9f0a, #ffd60a)",
];

export function logoColor(name) {
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 997;
  return GRADIENTS[h % GRADIENTS.length];
}

export function timeAgo(iso) {
  const then = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  const hours = Math.floor((Date.now() - then.getTime()) / 3600000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "1 day ago" : `${days} days ago`;
}

export function salary(job) {
  if (job.salary_min_lpa == null || job.salary_max_lpa == null) return "Not disclosed";
  return `${job.salary_min_lpa} - ${job.salary_max_lpa} LPA`;
}