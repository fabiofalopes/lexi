from agent import run_search_and_synthesize_workflow
import os

if __name__ == "__main__":
    print("Lexi Owl Main Entry Point Activated")

    # --- Configuration ---
    #USER_QUERY = "What are the latest advancements in AI?"
    #USER_QUERY = "Cria-me um guia de termos sobre apicultura especialmente para o contexto de portugal e ainda mais especialmente para o contexto de Pampilhosa da Serra, Coimbra, Portugal. Termos sobre apicultura em geral, detalhes, particularidades, etc, mas especificamente e principalmente partes tecnicas de apicultura e abelhas. Preciso de paralelismos com termos conhecidos em inglês também se for conveniente, mas o principal e termos um guia completo ter termos."
    USER_QUERY = "Como me tornar advogado em portugal?"
    
    MODEL_NAME = "meta-llama/llama-4-maverick-17b-128e-instruct"  # Groq model
    TEMPERATURE = 0.1
    NUM_ITERATIONS = 2
    SEARCH_RESULTS_PER_ITER = 2
    JINA_API_KEY = os.environ.get("JINA_API_KEY", "YOUR_JINA_API_KEY")
    #OUTPUT_DIR_NAME = "main_agent_run_output"
    OUTPUT_DIR_NAME = "OUTTT"
    YOUTUBE_TRANSCRIPT_LANGUAGES = ['en', 'pt']
    DELAY = 1.0

    # Check for required Groq API key
    if not os.environ.get("GROQ_API_KEY"):
        print("[WARNING] GROQ_API_KEY is not set in your environment. LLM calls will fail unless you set it in your .env or environment variables.")

    # --- Execute Workflow ---
    try:
        run_search_and_synthesize_workflow(
            user_question=USER_QUERY,
            model_name=MODEL_NAME,
            temperature=TEMPERATURE,
            num_iterations=NUM_ITERATIONS,
            search_results_per_iter=SEARCH_RESULTS_PER_ITER,
            output_dir=OUTPUT_DIR_NAME,
            jina_api_key=JINA_API_KEY,
            youtube_transcript_languages=YOUTUBE_TRANSCRIPT_LANGUAGES,
            delay=DELAY
        )
        print(f"Workflow execution finished. Check the '{OUTPUT_DIR_NAME}' folder.")
    except Exception as e:
        print(f"An error occurred during workflow execution: {e}") 