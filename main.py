from src.core.agent import research_workflow
from src.core.config import AgentConfig
import os

if __name__ == "__main__":
    print("Lexi Owl Main Entry Point Activated")

    # --- Configuration ---
    #USER_QUERY = "What are the latest advancements in AI?"
    #USER_QUERY = "Cria-me um guia de termos sobre apicultura especialmente para o contexto de portugal e ainda mais especialmente para o contexto de Pampilhosa da Serra, Coimbra, Portugal. Termos sobre apicultura em geral, detalhes, particularidades, etc, mas especificamente e principalmente partes tecnicas de apicultura e abelhas. Preciso de paralelismos com termos conhecidos em inglês também se for conveniente, mas o principal e termos um guia completo ter termos."
    #USER_QUERY = "Como me tornar advogado em portugal?"
    
    
    #USER_QUERY = '''
    #    I am conducting an academic analysis of the **Citymapper** mobile application for a Mobile Computing course at Universidade Lusófona. I need comprehensive information about **Citymapper** to create a 4-6 minute presentation that demonstrates advanced understanding of mobile computing concepts. For this **Citymapper** analysis, I require detailed information about how **Citymapper** solves urban navigation problems, what technical advantages **Citymapper** offers over traditional solutions, and how **Citymapper** leverages mobile-specific technologies. I need to understand **Citymapper's** usability design, navigation mechanisms, connectivity requirements, and how **Citymapper** uses geolocation and sensors. Additionally, I must analyze **Citymapper's** business model, user reviews, competitive positioning against Google Maps and other navigation apps, and **Citymapper's** battery consumption patterns. The research should also cover **Citymapper's** technical architecture, data sources, offline capabilities, and any innovative features that distinguish **Citymapper** from competitors. I need concrete data, user statistics, and technical specifications about **Citymapper** to support a critical analysis that goes beyond basic app description and demonstrates sophisticated mobile computing knowledge. Please focus on finding specific, factual information about **Citymapper** from official sources, app stores, tech publications, and user feedback platforms.
    #'''
    
    USER_QUERY = '''
        Preciso de investigar a aplicação móvel Citymapper para um projeto académico, com foco específico na sua utilização em Lisboa. Por favor, encontre informação detalhada sobre como o Citymapper funciona em Lisboa, que problemas de mobilidade urbana o Citymapper resolve na capital portuguesa, quem desenvolveu o Citymapper, e quando o Citymapper foi lançado em Lisboa. Preciso de saber sobre as funcionalidades do Citymapper disponíveis para Lisboa, como o Citymapper utiliza GPS e sensores para navegar pelas ruas lisboetas, que dados o Citymapper necessita dos servidores dos transportes públicos de Lisboa (Metro, Carris, CP, ferries), e como o Citymapper se compara com o Google Maps na navegação por Lisboa. Investigue também o modelo de negócio do Citymapper, avaliações dos utilizadores lisboetas do Citymapper, consumo de bateria do Citymapper, e quaisquer tecnologias inovadoras que o Citymapper utiliza especificamente para Lisboa. Encontre informação sobre o design da interface do Citymapper adaptado a Lisboa, métodos de navegação do Citymapper pelas colinas e ruas estreitas de Lisboa, e capacidades offline do Citymapper na cidade. Preciso de factos concretos e estatísticas sobre o Citymapper em Lisboa para analisar como esta app está a transformar a mobilidade urbana na capital portuguesa para a minha apresentação do curso de Computação Móvel.
    '''
    
    #USER_QUERY = '''
    #    
    #'''
    
    MODEL_NAME = "meta-llama/llama-4-maverick-17b-128e-instruct"  # Groq model
    TEMPERATURE = 0.1
    NUM_ITERATIONS = 15
    SEARCH_RESULTS_PER_ITER = 5
    JINA_API_KEY = os.environ.get("JINA_API_KEY", "YOUR_JINA_API_KEY")
    #OUTPUT_DIR_NAME = "main_agent_run_output"
    OUTPUT_DIR_NAME = "Citymapper_Analysis2"
    YOUTUBE_TRANSCRIPT_LANGUAGES = ['en', 'pt']
    DELAY = 1.0

    # Check for required Groq API key
    if not os.environ.get("GROQ_API_KEY"):
        print("[WARNING] GROQ_API_KEY is not set in your environment. LLM calls will fail unless you set it in your .env or environment variables.")

    # --- Execute Workflow ---
    try:
        config = AgentConfig(
            model_name=MODEL_NAME,
            temperature=TEMPERATURE,
            num_iterations=NUM_ITERATIONS,
            num_search_results_per_iteration=SEARCH_RESULTS_PER_ITER,
            output_dir=OUTPUT_DIR_NAME,
            jina_api_key=JINA_API_KEY,
            youtube_transcript_languages=YOUTUBE_TRANSCRIPT_LANGUAGES,
            delay=DELAY
        )
        result = research_workflow(user_question=USER_QUERY, config=config)
        print(f"Workflow execution finished. Check the '{OUTPUT_DIR_NAME}' folder.")
    except Exception as e:
        print(f"An error occurred during workflow execution: {e}")

# The agentic workflow and LLM logic are now modular and separated with clean public API 