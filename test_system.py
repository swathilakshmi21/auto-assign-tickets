"""Quick test script to verify system components without UI"""
import sys
import pandas as pd

def test_data_loading():
    """Test if data can be loaded"""
    print("=" * 60)
    print("TEST 1: Data Loading")
    print("=" * 60)
    
    try:
        from src.data.loader import DataLoader
        
        loader = DataLoader()
        roster_df, incidents_df = loader.load_all()
        
        print(f"✅ Roster loaded: {len(roster_df)} people")
        print(f"✅ Incidents loaded: {len(incidents_df)} incidents")
        
        # Check columns
        print("\n📋 Roster columns:")
        print(roster_df.columns.tolist())
        print("\n📋 Incident columns:")
        print(incidents_df.columns.tolist())
        
        return True, roster_df, incidents_df
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False, None, None

def test_matching(roster_df, incidents_df):
    """Test matching engine"""
    print("\n" + "=" * 60)
    print("TEST 2: Matching Engine")
    print("=" * 60)
    
    try:
        from src.core.matcher import Matcher
        
        matcher = Matcher(roster_df)
        
        # Test with first incident
        if len(incidents_df) > 0:
            incident = incidents_df.iloc[0].to_dict()
            candidates = matcher.find_candidates(incident)
            
            print(f"✅ Found {len(candidates)} candidates for incident")
            print(f"📋 Incident: {incident.get('short_description', 'N/A')[:50]}")
            print(f"📋 Subcategory: {incident.get('subcategory', 'N/A')}")
            
            return True
        else:
            print("⚠️ No incidents to test")
            return False
            
    except Exception as e:
        print(f"❌ Error in matching: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scoring(roster_df, incidents_df):
    """Test scoring engine"""
    print("\n" + "=" * 60)
    print("TEST 3: Scoring Engine")
    print("=" * 60)
    
    try:
        from src.core.matcher import Matcher
        from src.core.scorer import Scorer
        
        matcher = Matcher(roster_df)
        scorer = Scorer(matcher)
        
        if len(incidents_df) > 0:
            incident = incidents_df.iloc[0].to_dict()
            candidates = matcher.find_candidates(incident)
            
            if len(candidates) > 0:
                scored = scorer.calculate_scores(incident, candidates)
                
                print(f"✅ Scored {len(scored)} candidates")
                print("\n📊 Top 3 candidates:")
                
                for i, (idx, row) in enumerate(scored.head(3).iterrows(), 1):
                    user_id = row.get('user_id', 'N/A')
                    total_score = row.get('total_score', 0)
                    print(f"  {i}. User {user_id}: Score = {total_score}")
                
                return True
            else:
                print("⚠️ No candidates to score")
                return False
        else:
            print("⚠️ No incidents to test")
            return False
            
    except Exception as e:
        print(f"❌ Error in scoring: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_connection():
    """Test LLM connection"""
    print("\n" + "=" * 60)
    print("TEST 4: LLM Connection")
    print("=" * 60)
    
    try:
        from src.utils.llm_client import LLMClient
        
        client = LLMClient()
        print("✅ LLM client initialized")
        print("Note: Actual API call not tested (would cost tokens)")
        return True
        
    except ValueError as e:
        print(f"⚠️ No LLM config (using fallback): {e}")
        return False
    except Exception as e:
        print(f"❌ LLM error: {e}")
        return False

def test_storage():
    """Test storage"""
    print("\n" + "=" * 60)
    print("TEST 5: Storage")
    print("=" * 60)
    
    try:
        from src.data.storage import Storage
        
        storage = Storage()
        stats = storage.get_statistics()
        
        print("✅ Storage initialized")
        print(f"📊 Stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Storage error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "🚀 " * 20)
    print(" AUTO TICKET ASSIGNMENT - SYSTEM TEST")
    print("🚀 " * 20 + "\n")
    
    # Test 1: Data Loading
    success, roster_df, incidents_df = test_data_loading()
    
    if not success:
        print("\n❌ CRITICAL: Cannot load data. Please check Excel files.")
        sys.exit(1)
    
    # Test 2: Matching
    match_success = test_matching(roster_df, incidents_df)
    
    # Test 3: Scoring
    score_success = test_scoring(roster_df, incidents_df)
    
    # Test 4: LLM (optional)
    llm_success = test_llm_connection()
    
    # Test 5: Storage
    storage_success = test_storage()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    tests = [
        ("Data Loading", True),  # Already passed
        ("Matching Engine", match_success),
        ("Scoring Engine", score_success),
        ("LLM Connection", llm_success),  # Optional
        ("Storage", storage_success)
    ]
    
    for test_name, passed in tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_required_passed = all([
        True,  # Data loading
        match_success,
        score_success,
        storage_success
    ])
    
    if all_required_passed:
        print("\n" + "✅ " * 20)
        print("ALL REQUIRED TESTS PASSED!")
        print("✅ System is ready to use!")
        print("Run 'streamlit run app.py' to start the UI")
        print("✅ " * 20 + "\n")
    else:
        print("\n❌ Some tests failed. Please check errors above.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()

