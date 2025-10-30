# 🎫 Auto Ticket Assignment - AI Agent POC

An intelligent, AI-powered ticket assignment system that uses LLM reasoning to provide top-K recommendations with minimal human intervention.

## ✨ Features

- 🤖 **AI Agent**: LLM-powered reasoning for intelligent recommendations
- 🎯 **Smart Matching**: Skills, shift timing, on-call status, capacity
- 👤 **Human-in-the-Loop**: Accept or Override decisions
- 📊 **Audit Trail**: Complete tracking of assignments and metrics
- 🎨 **Beautiful UI**: Modern Streamlit interface with real-time KPIs
- 🔍 **Top-K Suggestions**: Shows top 3 candidates with detailed explanations

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Azure OpenAI account and credentials

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Create a `.env` file (see `env_example.txt`):

```env
LLM_Wrapper_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_KEY=your-key-here
OPENAI_API_VERSION=2024-02-15-preview
```

### Prepare Data

Place Excel files in `inputs/`:
- Roster: `dummy_roster_servicenow.xlsx`
- Incidents: `incidents.xlsx`

### Run

```bash
streamlit run app.py
```

## 📐 Architecture

```
src/
├── agents/              # AI Agent orchestration
├── core/                # Matching, scoring, LLM reasoning
├── data/                # Loading and storage
├── utils/               # Configuration and LLM client
└── ui/                  # Streamlit UI components
```

## 🎯 How It Works

1. **Matching**: Filters candidates by skill, shift, availability
2. **Scoring**: Calculates multi-factor scores
3. **AI Reasoning**: LLM analyzes context and provides recommendations
4. **Human Decision**: Accept top recommendation or override
5. **Storage**: Saves assignment with full audit trail
6. **Analytics**: Tracks acceptance rate, time saved, violations

## 📊 Key Metrics

- **Acceptance Rate**: Goal ≥70%
- **Time-to-First-Response**: Goal ≥25% faster
- **Policy Violations**: Goal 0
- **Reassignments**: Tracked and trending down

## 🔧 Scoring Algorithm

Candidates are scored on:
- **Skill Match** (50 pts): Subcategory matching skills
- **On-Call Boost** (50+ pts): Bonus for on-call staff
- **Shift Timing** (30 pts): Within shift hours
- **Availability** (30 pts): Based on max_concurrent capacity

## 📝 Project Structure

```
├── src/                    # Source code
│   ├── agents/           # AI Agent
│   ├── core/             # Matching & Scoring
│   ├── data/             # Data handling
│   ├── utils/            # Utilities
│   └── ui/               # Streamlit UI
├── inputs/               # Input Excel files
├── outputs/              # Generated assignments
├── app.py                # Main Streamlit app
└── requirements.txt      # Dependencies
```

## 🎨 UI Components

### Dashboard
- Real-time KPI metrics
- Acceptance rate with progress bars
- Recent incidents list

### Assignment Interface
- Select incident
- View AI recommendations
- Accept or Override
- Top-K display (default 3)

### Audit & Analytics
- Assignment history
- Filterable data
- Export to CSV
- Performance tracking

## 🚨 Troubleshooting

**LLM Connection Issues?**
- Check `.env` credentials
- Falls back to score-based recommendations

**No Candidates Found?**
- Verify skill matching
- Check subcategory spelling

**UI Not Loading?**
- Ensure Python 3.8+
- Run `pip install -r requirements.txt`

## 📚 Documentation

- `README_POC.md` - Detailed POC documentation
- `POC_SUMMARY.md` - Quick start guide
- `env_example.txt` - Environment template

## 🔮 Future Enhancements

- ServiceNow API integration
- Webhook support for real-time updates
- Multi-team routing
- Learning loop for continuous improvement
- Advanced analytics dashboard

## 📄 License

MIT License

## 👥 Author

American Airlines IT Department

