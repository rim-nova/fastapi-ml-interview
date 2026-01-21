from textblob import TextBlob
import random
import time


class SentimentModel:
    """
    Real NLP Engine using TextBlob.
    Simulates version differences by using different logic paths.
    """

    @staticmethod
    def predict(text: str, version: str) -> tuple[str, float]:
        blob = TextBlob(text)

        # --- Version 1.0.0 (The "Fast but Simple" Model) ---
        if version == "1.0.0":
            # Simulate older model: Fast execution, simple polarity check
            time.sleep(0.05)
            polarity = blob.sentiment.polarity

            if polarity > 0:
                return "positive", 0.5 + (abs(polarity) / 2)
            elif polarity < 0:
                return "negative", 0.5 + (abs(polarity) / 2)
            else:
                return "neutral", 0.5

        # --- Version 2.0.0 (The "Slow but Smart" Model) ---
        elif version == "2.0.0":
            # Simulate complex model: Slower, uses subjectivity to weigh confidence
            time.sleep(0.15)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity

            # Logic: If text is subjective, polarity is more likely to be accurate sentiment
            adjusted_score = polarity * (1 + (subjectivity * 0.5))

            if adjusted_score > 0.1:
                conf = 0.6 + (abs(polarity) * 0.4)
                return "positive", min(conf, 0.99)
            elif adjusted_score < -0.1:
                conf = 0.6 + (abs(polarity) * 0.4)
                return "negative", min(conf, 0.99)
            else:
                return "neutral", 0.6

        # Fallback
        return "unknown", 0.0
