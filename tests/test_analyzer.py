import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from resume_analyzer.analyzer import ResumeAnalyzer, extract_skills
from resume_analyzer.extraction import extract_text
from resume_analyzer.presentation import escape_html
from resume_analyzer.text import cosine_similarity, redact_personal_data


class ResumeAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.resume = (ROOT / "sample_data" / "resume.txt").read_text(encoding="utf-8")
        self.job = (ROOT / "sample_data" / "job-description.txt").read_text(encoding="utf-8")
        self.analysis = ResumeAnalyzer().analyze(self.resume, self.job)

    def test_scores_and_gaps(self):
        self.assertGreater(self.analysis.scores.overall, 45)
        self.assertIn("python", self.analysis.matched_skills)
        self.assertIn("terraform", self.analysis.missing_skills)

    def test_similarity_is_bounded(self):
        score = cosine_similarity(self.resume, self.job)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)

    def test_personal_data_redaction(self):
        redacted = redact_personal_data("Sam Person\nsam@example.com +1 (555) 123-4567")
        self.assertIn("[NAME]", redacted)
        self.assertNotIn("sam@example.com", redacted)
        self.assertIn("[PHONE]", redacted)

    def test_text_extraction(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "resume.txt"
            path.write_text(self.resume, encoding="utf-8")
            self.assertEqual(extract_text(path), self.resume)

    def test_report_serializes(self):
        payload = json.dumps(self.analysis.to_dict())
        self.assertIn("Career guidance only", payload)

    def test_html_boundary_escapes_skill_content(self):
        self.assertEqual(escape_html('<img src=x onerror="alert(1)">'), "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;")

    def test_azure_deployment_assets_are_wired_for_cloud_dependencies(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        bicep = (ROOT / "deploy" / "azure" / "main.bicep").read_text(encoding="utf-8")
        deploy = (ROOT / "deploy" / "azure" / "deploy.sh").read_text(encoding="utf-8")
        pipeline = (ROOT / "deploy" / "azure" / "azure-pipelines.yml").read_text(encoding="utf-8")
        self.assertIn("ARG REQUIREMENTS_FILE=requirements.txt", dockerfile)
        self.assertIn("requirements-cloud.txt", deploy)
        self.assertIn("Microsoft.App/containerApps", bicep)
        self.assertIn("/_stcore/health", bicep)
        self.assertIn("secretRef: 'openai-api-key'", bicep)
        self.assertIn("AzureCLI@2", pipeline)
        self.assertNotIn("OPENAI_API_KEY=sk-", bicep + deploy + pipeline)


if __name__ == "__main__":
    unittest.main()
