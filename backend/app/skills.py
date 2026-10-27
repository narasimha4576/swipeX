import re

SKILL_ALIASES = {
    "Python": ["python"],
    "Java": ["java"],
    "JavaScript": ["javascript"],
    "TypeScript": ["typescript"],
    "React": ["react", "react.js", "reactjs"],
    "Node.js": ["node.js", "nodejs"],
    "SQL": ["sql"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb"],
    "Redis": ["redis"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Terraform": ["terraform"],
    "Git": ["git"],
    "CI/CD": ["ci/cd", "cicd", "continuous integration"],
    "REST APIs": ["rest api", "rest apis", "restful"],
    "GraphQL": ["graphql"],
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Flask": ["flask"],
    "Spring Boot": ["spring boot", "springboot"],
    "Machine Learning": ["machine learning"],
    "Deep Learning": ["deep learning"],
    "NLP": ["nlp", "natural language processing"],
    "Computer Vision": ["computer vision"],
    "PyTorch": ["pytorch"],
    "TensorFlow": ["tensorflow"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Spark": ["spark", "pyspark"],
    "Airflow": ["airflow"],
    "Kafka": ["kafka"],
    "Hadoop": ["hadoop"],
    "Snowflake": ["snowflake"],
    "dbt": ["dbt"],
    "LLMs": ["llm", "llms", "large language model", "large language models"],
    "RAG": ["rag", "retrieval-augmented generation", "retrieval augmented generation"],
    "LangChain": ["langchain"],
    "Generative AI": ["generative ai", "genai"],
    "Tableau": ["tableau"],
    "Power BI": ["power bi", "powerbi"],
    "Excel": ["excel"],
    "Statistics": ["statistics", "statistical"],
    "Data Analysis": ["data analysis", "data analytics"],
    "A/B Testing": ["a/b testing", "ab testing"],
    "Go": ["golang"],
    "Rust": ["rust"],
    "C++": ["c++"],
    "C#": ["c#"],
    ".NET": [".net"],
    "Ruby": ["ruby"],
    "Kotlin": ["kotlin"],
    "Android": ["android"],
    "iOS": ["ios"],
    "HTML": ["html"],
    "CSS": ["css"],
    "Linux": ["linux"],
    "Microservices": ["microservices", "microservice"],
    "System Design": ["system design"],
    "Agile": ["agile", "scrum"],
    "Jira": ["jira"],
    "Selenium": ["selenium"],
    "Pytest": ["pytest"],
    "Elasticsearch": ["elasticsearch", "opensearch"],
    "Celery": ["celery"],
    "RabbitMQ": ["rabbitmq"],
    "Data Structures": ["data structures"],
    "Algorithms": ["algorithms"],
    "OOP": ["oop", "object-oriented", "object oriented"],
}

_PATTERNS = {
    skill: re.compile(
        "|".join(
            r"(?<![A-Za-z0-9+#])" + re.escape(alias) + r"(?![A-Za-z0-9+#])"
            for alias in aliases
        ),
        re.IGNORECASE,
    )
    for skill, aliases in SKILL_ALIASES.items()
}


def extract_skills(text: str, limit: int | None = None) -> list[str]:
    counts = {}
    for skill, pattern in _PATTERNS.items():
        found = len(pattern.findall(text or ""))
        if found:
            counts[skill] = found
    ordered = sorted(counts, key=lambda s: (-counts[s], s))
    return ordered[:limit] if limit else ordered