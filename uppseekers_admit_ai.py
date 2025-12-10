import pandas as pd
import os
import sys

# --- Configuration ---
# File names correspond to the CSVs generated from your original Excel sheets.
# The structure of the code is designed to load all sheets dynamically.

# Base file names for the two source files
READY_FILE = "University Readiness_new (1).xlsx"
BENCHMARK_FILE = "Benchmarking_USA.xlsx"

# Mapping sheet names (which should now be CSV files)
COURSE_TO_QUESTION_MAP_FILE = f"{READY_FILE} - Sheet1.csv"
COURSE_TO_BENCHMARK_MAP_FILE = f"{BENCHMARK_FILE} - Sheet1.csv"

# --- Utility Functions ---

def load_data():
    """
    Loads all required data (question sets, benchmark sets, and mappings)
    from the provided CSV files into DataFrames.
    """
    print("Loading data files...")
    data = {}
    try:
        # 1. Load Course Mappings
        course_q_map_df = pd.read_csv(COURSE_TO_QUESTION_MAP_FILE)
        data['course_q_map'] = course_q_map_df.set_index('course').to_dict()['next_questions_set']

        course_b_map_df = pd.read_csv(COURSE_TO_BENCHMARK_MAP_FILE)
        data['course_b_map'] = course_b_map_df.set_index('course').to_dict()['benchmarking_set']

        # 2. Dynamically Load Question Sets
        data['question_sets'] = {}
        for course, sheet_name in data['course_q_map'].items():
            file_name = f"{READY_FILE} - {sheet_name}.csv"
            data['question_sets'][course] = pd.read_csv(file_name)
        
        # 3. Dynamically Load Benchmark Sets
        data['benchmark_sets'] = {}
        for course, sheet_name in data['course_b_map'].items():
            file_name = f"{BENCHMARK_FILE} - {sheet_name}.csv"
            data['benchmark_sets'][course] = pd.read_csv(file_name)

        print("Data loaded successfully.")

    except FileNotFoundError as e:
        print(f"\nFATAL ERROR: Required data file not found: {e.filename}")
        print("Please ensure all required CSV files are in the same directory as this script.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred during data loading: {e}")
        sys.exit(1)
        
    return data

def get_user_scores(course, question_df):
    """
    Runs the interactive questionnaire for the selected course and collects scores.
    """
    user_scores = {}
    total_score = 0
    max_score = 0
    
    # Identify score and option columns dynamically (e.g., score_A, option_A)
    score_cols = [col for col in question_df.columns if col.startswith('score_')]
    option_cols = [col.replace('score_', 'option_') for col in score_cols]
    
    print(f"\n--- University Readiness Questionnaire for {course} ---")
    
    for _, row in question_df.iterrows():
        q_id = f"Q{row['question_id']}"
        q_text = row['question_text']
        
        # Calculate the maximum score for this question
        current_q_max = max([row[s_col] for s_col in score_cols if pd.notna(row[s_col])], default=0)
        max_score += current_q_max

        print(f"\n{q_id}. {q_text}")
        
        options = {}
        for i, (opt_col, scr_col) in enumerate(zip(option_cols, score_cols)):
            option_text = row.get(opt_col)
            score_value = row.get(scr_col)
            
            # Stop if we hit a NaN option, assuming options are contiguous
            if pd.isna(option_text) or pd.isna(score_value):
                break
                
            key = str(i + 1)
            options[key] = {'text': option_text, 'score': score_value}
            print(f"  [{key}] {option_text} (Score: {score_value})")

        while True:
            choice = input("Enter your choice number (e.g., 1): ")
            if choice in options:
                user_selected_score = options[choice]['score']
                user_scores[q_id] = user_selected_score
                total_score += user_selected_score
                break
            else:
                print("Invalid choice. Please enter the corresponding number.")

    print("\n--- Questionnaire Complete ---")
    return user_scores, total_score, max_score

def calculate_report(course, user_scores, user_total, max_score, benchmark_df):
    """
    Calculates the detailed comparison report against university benchmarks.
    """
    print(f"\n--- Generating Detailed Report for {course} Admissions Readiness ---")
    
    report_data = []
    
    # 1. Identify Q-columns in the benchmark data (Q1, Q2, Q3, etc.)
    q_cols = [col for col in benchmark_df.columns if col.startswith('Q')]
    
    if not q_cols:
        print("Error: Benchmark file does not contain 'Q' columns (Q1, Q2, etc.). Cannot generate detailed report.")
        return

    # 2. Calculate User's Overall Readiness Percentage
    user_readiness_percent = (user_total / max_score) * 100 if max_score > 0 else 0
    
    # 3. Process each university
    for _, university_row in benchmark_df.iterrows():
        uni_name = university_row['University']
        uni_total_benchmark = university_row['Total Benchmark Score']
        
        # Calculate University's Overall Readiness Percentage
        # We must use the user's max_score (derived from the question set)
        uni_readiness_percent = (uni_total_benchmark / max_score) * 100 if max_score > 0 else 0
        
        # Calculate Gap
        score_gap = uni_total_benchmark - user_total
        percent_gap = ((uni_total_benchmark - user_total) / uni_total_benchmark) * 100 if uni_total_benchmark > 0 else 100
        
        # Prepare detailed criterion breakdown
        breakdown = {}
        for q_id in q_cols:
            user_q_score = user_scores.get(q_id, 0)
            uni_q_benchmark = university_row.get(q_id, 0)
            
            # Handle potential case where the benchmark sheet is missing a Q column
            if pd.isna(uni_q_benchmark):
                uni_q_benchmark = 0.0

            breakdown[q_id] = {
                'user_score': user_q_score,
                'uni_benchmark': uni_q_benchmark,
                'gap': uni_q_benchmark - user_q_score
            }
            
        report_data.append({
            'University': uni_name,
            'User Score': user_total,
            'Benchmark Score': uni_total_benchmark,
            'User Readiness %': f"{user_readiness_percent:.1f}%",
            'Benchmark Readiness %': f"{uni_readiness_percent:.1f}%",
            'Score Gap (Abs)': score_gap,
            'Gap %': f"{percent_gap:.1f}%",
            'Criterion Breakdown': breakdown
        })

    # Sort the report by Score Gap (smallest gap first)
    report_data.sort(key=lambda x: x['Score Gap (Abs)'])
    
    return report_data, user_readiness_percent, max_score

def display_report(report_data, user_readiness_percent, max_score, course):
    """
    Displays the generated report in a readable format.
    """
    
    print("\n" + "="*80)
    print(f"| {'UPPSEEKERS ADMISSIONS READINESS REPORT':^76} |")
    print(f"| {'Target Course: ' + course:^76} |")
    print("="*80)
    
    print(f"\n[SUMMARY] User's Overall Readiness Score: {report_data[0]['User Score']:.1f} / {max_score:.1f} ({user_readiness_percent:.1f}%)")
    
    print("\n[UNIVERSITY BENCHMARK COMPARISON]")
    
    # Create a nice summary table
    summary_table = []
    
    for item in report_data:
        summary_table.append({
            'University': item['University'],
            'User %': item['User Readiness %'],
            'Benchmark %': item['Benchmark Readiness %'],
            'Gap %': item['Gap %']
        })
        
    summary_df = pd.DataFrame(summary_table)
    
    # Highlight the best matches (smallest gaps)
    print(summary_df.to_markdown(index=False))
    
    print("\n[TOP 3 DEVELOPMENT AREAS]")
    
    # 4. Generate Top 3 Development Areas (Focus on the university with the smallest positive gap or the top benchmark)
    
    # Get the top university by benchmark score
    top_uni = max(report_data, key=lambda x: x['Benchmark Score'])
    top_uni_breakdown = top_uni['Criterion Breakdown']
    
    # Calculate the gap for each criterion for the top university
    gaps = []
    for q_id, data in top_uni_breakdown.items():
        if data['gap'] > 0:
            gaps.append({
                'criterion': q_id,
                'gap': data['gap'],
                'uni_score': data['uni_benchmark']
            })
            
    # Sort by the largest positive gap (areas where the user needs most improvement relative to the top university)
    gaps.sort(key=lambda x: x['gap'], reverse=True)
    
    if gaps:
        for i, gap in enumerate(gaps[:3]):
            # Find the actual question text for better context
            question_row = question_sets[course].loc[question_sets[course]['question_id'] == int(gap['criterion'].replace('Q', ''))].iloc[0]
            question_text = question_row['question_text']
            
            print(f"  {i+1}. {question_text} ({gap['criterion']})")
            print(f"     Required Score (Top University): {gap['uni_score']:.1f}")
            print(f"     Your Score: {user_scores[gap['criterion']]:.1f}")
            print(f"     Score Gap: {gap['gap']:.1f}")
            
    print("\n" + "="*80)
    print("This report is a guide. Contact an Uppseekers counselor for a personalized strategy.")
    print("="*80 + "\n")


def main():
    """
    Main execution function.
    """
    global question_sets # Needs to be global for use in display_report
    
    # 1. Load Data
    data = load_data()
    question_sets = data['question_sets']
    benchmark_sets = data['benchmark_sets']
    course_q_map = data['course_q_map']
    
    available_courses = list(course_q_map.keys())

    # 2. Select Course
    print("\nAvailable Courses:")
    for i, course in enumerate(available_courses):
        print(f"[{i+1}] {course}")
        
    while True:
        try:
            choice = input("Enter the number of your target course: ")
            course_index = int(choice) - 1
            if 0 <= course_index < len(available_courses):
                selected_course = available_courses[course_index]
                break
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")
            
    # 3. Run Questionnaire
    question_df = question_sets[selected_course]
    user_scores, user_total, max_score = get_user_scores(selected_course, question_df)
    
    # 4. Calculate and Display Report
    benchmark_df = benchmark_sets[selected_course]
    report_data, user_readiness_percent, max_score = calculate_report(
        selected_course, user_scores, user_total, max_score, benchmark_df
    )
    
    display_report(report_data, user_readiness_percent, max_score, selected_course)

if __name__ == "__main__":
    main()
