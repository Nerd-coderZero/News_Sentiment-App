import json
import os

# Create directory for test data
os.makedirs("data/test_articles", exist_ok=True)

# Create test articles with clear sentiment signals
test_articles = [
    {
        "title": "Tesla Reports Record-Breaking Quarter with 200% Profit Increase",
        "content": """
        Tesla has announced extraordinary financial results for Q4, with profits soaring 200% year-over-year, dramatically exceeding analyst expectations. CEO Elon Musk called it "the best quarter in Tesla's history." The company has successfully ramped up production at all factories, with the Model Y becoming the best-selling vehicle globally. Supply chain issues that plagued the industry have been completely resolved for Tesla, while competitors continue to struggle. The company also announced three new gigafactories to be built in strategic locations, expected to triple Tesla's production capacity by 2026. Investors reacted enthusiastically, with the stock jumping 15% in after-hours trading. Analysts have upgraded their price targets significantly, with Goldman Sachs setting a new high target of $950 per share. The company's revolutionary new battery technology has achieved energy density improvements of 35%, far ahead of industry competitors.
        """
    },
    {
        "title": "Apple Innovation Stalls as iPhone Sales Plummet 30%",
        "content": """
        Apple reported a devastating 30% drop in iPhone sales this quarter, marking the company's worst performance in over a decade. Consumer interest in the iPhone 15 has been described as "alarmingly low" by industry analysts, with widespread complaints about lack of innovation and premium pricing. The company has delayed its highly anticipated mixed reality headset for the third time due to "significant technical challenges." CEO Tim Cook faced hostile questions during the earnings call, with one analyst asking if Apple had "lost its innovative edge." Several key executives have departed in recent months, including the head of product design and chief technology officer, creating leadership turmoil. Competitors like Samsung and Google have gained substantial market share with their latest devices featuring cutting-edge AI capabilities that Apple lacks. The company has also announced a hiring freeze and potential layoffs affecting up to 8,000 employees as cost-cutting measures. Apple stock has declined 25% year-to-date, underperforming the broader tech sector by a wide margin.
        """
    },
    {
        "title": "Microsoft Cloud Division Shows Moderate Growth Amid Mixed Earnings",
        "content": """
        Microsoft announced quarterly results that showed mixed performance across its business units. The company's cloud division, Azure, grew by 27%, slightly below the expected 29% but still maintaining strong momentum in the competitive cloud market. Office 365 subscriptions increased by 12%, in line with analyst expectations. The company's gaming division saw modest gains following the acquisition of Activision Blizzard, though integration challenges have slowed some planned releases. CEO Satya Nadella emphasized Microsoft's commitment to AI integration across all products, though some analysts questioned the pace of implementation compared to competitors. The Windows operating system saw flat growth as PC sales remain sluggish globally. Microsoft announced a slight increase in its dividend, maintaining its appeal to value investors. The company faces regulatory challenges in Europe regarding data privacy concerns, though executives expressed confidence in resolving these issues. Overall, the results painted a picture of steady performance with some areas of concern balanced by pockets of strength.
        """
    }
]

# Write test articles to files
for i, article in enumerate(test_articles):
    with open(f"data/test_articles/article_{i+1}.json", "w") as f:
        json.dump(article, f, indent=2)

print(f"Created {len(test_articles)} test articles in data/test_articles/")