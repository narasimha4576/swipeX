import re
from dataclasses import dataclass, field

OFFICIAL_SOURCES = ("greenhouse", "lever", "ashby")


@dataclass
class Flag:
    severity: str
    text: str


@dataclass
class Result:
    level: str
    flags: list = field(default_factory=list)
    good: list = field(default_factory=list)


# (severity, pattern, message, also checked on official company boards)
RULES = [
    (
        "high",
        re.compile(
            r"(registration|processing|training|security|joining|refundable|application|kit|laptop|equipment)"
            r"\s*(fee|fees|deposit|charges?|amount)"
            r"|pay\s+(a\s+)?(small\s+)?(fee|deposit|amount)"
            r"|(send|transfer|deposit)\s+(money|payment|rs\.?|inr|\u20b9)",
            re.I,
        ),
        "The posting asks you to pay money. Real employers never charge candidates.",
        True,
    ),
    (
        "high",
        re.compile(
            r"(aadhaar|aadhar|pan card|bank (account|details)|otp|cvv|passport copy).{0,40}(send|share|submit|provide)"
            r"|(send|share|submit|provide).{0,40}(aadhaar|aadhar|pan card|bank (account|details)|otp|cvv)",
            re.I,
        ),
        "It asks for ID documents, bank details or an OTP at the application stage.",
        True,
    ),
    (
        "medium",
        re.compile(
            r"(whats\s?app|telegram)\b.{0,60}(contact|message|apply|number|chat)"
            r"|(contact|message|apply|send).{0,60}(whats\s?app|telegram)|wa\.me/|t\.me/",
            re.I,
        ),
        "It asks you to apply or talk only through WhatsApp or Telegram.",
        False,
    ),
    (
        "medium",
        re.compile(
            r"\b[a-z0-9._%+-]+@(gmail|yahoo|ymail|outlook|hotmail|rediffmail|proton(mail)?)\.(com|in|me)\b",
            re.I,
        ),
        "It uses a personal email address instead of a company address.",
        False,
    ),
    (
        "medium",
        re.compile(
            r"(earn|income|salary).{0,25}(per day|a day|daily|per week|weekly)"
            r"|guaranteed\s+(job|placement|income|salary)|100%\s*(placement|job|guarantee)"
            r"|no\s+(interview|experience\s+(needed|required))|easy\s+money|get\s+rich",
            re.I,
        ),
        "It promises easy or guaranteed income.",
        False,
    ),
    (
        "medium",
        re.compile(r"\b(bit\.ly|tinyurl\.com|goo\.gl|cutt\.ly|rb\.gy)/", re.I),
        "It contains a shortened link, which hides where it leads.",
        False,
    ),
    (
        "low",
        re.compile(
            r"urgent(ly)?\s+hiring|immediate\s+joining|limited\s+(seats|slots|vacanc)|apply\s+(now|immediately)\s+before",
            re.I,
        ),
        "It pushes you to hurry. Take your time to check the company.",
        False,
    ),
]

WEIGHT = {"high": 3, "medium": 2, "low": 1}


def check_text(text: str, official: bool = False) -> list:
    flags = []
    for severity, pattern, message, applies_to_official in RULES:
        if official and not applies_to_official:
            continue
        if pattern.search(text or ""):
            flags.append(Flag(severity, message))
    return flags


def analyze(job, company) -> Result:
    official = job.source in OFFICIAL_SOURCES
    flags = check_text(f"{job.title}\n{job.description}", official=official)

    if company.verification_status != "verified":
        flags.append(
            Flag("medium", "This company is not verified. Check its website before sharing any details.")
        )
    if (
        job.experience_level == "fresher"
        and job.job_type == "full_time"
        and job.salary_max_lpa
        and job.salary_max_lpa > 40
    ):
        flags.append(Flag("medium", "The salary is unusually high for a fresher role."))

    good = []
    if company.verification_status == "verified":
        good.append("The company is verified on SwipeX.")
    if official:
        good.append("The job comes from the company's own official job board.")
    data = company.trust_data or {}
    age = (data.get("domain") or {}).get("age_years")
    if age is not None and age >= 2:
        good.append(f"The company website domain is {age} years old.")
    if data.get("wikidata"):
        good.append("The company appears in public records (Wikidata).")

    score = sum(WEIGHT[f.severity] for f in flags)
    if any(f.severity == "high" for f in flags) or score >= 5:
        level = "high"
    elif score >= 2:
        level = "medium"
    else:
        level = "low"
    return Result(level=level, flags=flags, good=good)