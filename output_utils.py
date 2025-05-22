"""
Helpers for saving agent run outputs in a structured, standardized way.
"""
import os
import json
from constants import FINAL_ANSWER_FILENAME, ALL_ITERATION_ANSWERS_FILENAME

def save_run_outputs(run_folder: str, user_question: str, final_answer: str, iteration_data: list, model_config: dict):
    """
    Save all outputs for a run in the specified run_folder.
    - final_answer.md: The synthesized answer.
    - all_iteration_answers.md: Details for each iteration (prompt, answer, URLs).
    - run_summary.json: Metadata/config for the run.
    """
    os.makedirs(run_folder, exist_ok=True)
    # Save final answer
    final_answer_path = os.path.join(run_folder, FINAL_ANSWER_FILENAME)
    with open(final_answer_path, 'w', encoding='utf-8') as f:
        f.write(final_answer)
    # Save all iteration details (Markdown)
    all_answers_path = os.path.join(run_folder, ALL_ITERATION_ANSWERS_FILENAME)
    with open(all_answers_path, 'w', encoding='utf-8') as f:
        for i, data in enumerate(iteration_data, 1):
            f.write(f"\n---\n\n# Iteration {i}\n\n")
            f.write(f"## Search Prompt:\n{data['search_prompt']}\n\n")
            f.write(f"## Brave Search URLs:\n" + "\n".join(data['urls']) + "\n\n")
            f.write(f"## Agentic Answer:\n{data['answer']}\n")
    # Save run summary/config (JSON)
    summary = {
        'user_question': user_question,
        'model_config': model_config,
        'num_iterations': len(iteration_data),
        'iteration_data': [
            {
                'search_prompt': d['search_prompt'],
                'urls': d['urls'],
            } for d in iteration_data
        ]
    }
    summary_path = os.path.join(run_folder, 'run_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False) 