# agent.py - Complete agents setup in single file
import os
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.adk.tools.tool_context import ToolContext
from . import prompt  # Import prompt from separate file

# ===== TOOLS =====
def generate_replication_prompt(tool_context: ToolContext) -> dict:
    """Genera prompt per replica sito basandosi sui dati di scraping"""
    
    scraping_data = tool_context.state.get("complete_site_data", {})
    
    if not scraping_data:
        return {"error": "Nessun dato di scraping trovato nello state"}
    
    # Estrarre dati dalla struttura JSON
    session_data = scraping_data.get("scraping_session", {})
    metadata = session_data.get("metadata", {})
    design_system = session_data.get("design_system", {})
    html_structure = session_data.get("html_structure", {})
    content_data = session_data.get("content_data", {})
    interactive_elements = session_data.get("interactive_elements", {})
    css_analysis = session_data.get("css_analysis", {})
    
    # Generare prompt dettagliato per replica
    generated_prompt = f"""
PROMPT PER REPLICA SITO WEB

TARGET URL: {metadata.get('target_url', 'N/A')}
DATA ANALISI: {metadata.get('timestamp', 'N/A')}
STATUS: {metadata.get('status', 'N/A')}

=== DESIGN SYSTEM ===
COLORI:
- Primario: {design_system.get('color_palette', {}).get('primary', 'N/A')}
- Secondario: {design_system.get('color_palette', {}).get('secondary', 'N/A')}
- Accent: {design_system.get('color_palette', {}).get('accent', 'N/A')}
- Background: {design_system.get('color_palette', {}).get('background', 'N/A')}
- Text: {design_system.get('color_palette', {}).get('text', 'N/A')}

TIPOGRAFIA:
- Font Heading: {design_system.get('typography', {}).get('heading_font', 'N/A')}
- Font Body: {design_system.get('typography', {}).get('body_font', 'N/A')}
- Font Sizes: {design_system.get('typography', {}).get('font_sizes', [])}

SPACING:
- Margins: {design_system.get('spacing', {}).get('margins', [])}
- Paddings: {design_system.get('spacing', {}).get('paddings', [])}

=== STRUTTURA HTML ===
Header: {str(html_structure.get('header', 'N/A'))[:200]}...
Navigation: {str(html_structure.get('navigation', 'N/A'))[:200]}...
Main Content: {str(html_structure.get('main_content', 'N/A'))[:200]}...
Footer: {str(html_structure.get('footer', 'N/A'))[:200]}...

=== CONTENUTI ===
Titolo Pagina: {content_data.get('page_title', 'N/A')}
Headings: {content_data.get('headings', [])}
Immagini: {len(content_data.get('images', []))} immagini trovate
Links: {len(content_data.get('links', []))} link trovati

=== ELEMENTI INTERATTIVI ===
Bottoni: {len(interactive_elements.get('buttons', []))} bottoni
Form: {len(interactive_elements.get('forms', []))} form
Menu di Navigazione: {interactive_elements.get('navigation_menus', [])}

=== ANALISI CSS ===
Layout System: {css_analysis.get('layout_system', 'N/A')}
Responsive Breakpoints: {css_analysis.get('responsive_breakpoints', [])}
Classi Importanti: {css_analysis.get('important_classes', [])}
Animazioni: {css_analysis.get('animations', [])}

=== ISTRUZIONI PER REPLICA ===
1. Usa questi colori esatti per mantenere la coerenza visiva
2. Replica la struttura HTML delle sezioni principali
3. Implementa il sistema di spacing definito
4. Ricrea gli elementi interattivi identificati
5. Usa il layout system specificato ({css_analysis.get('layout_system', 'flexbox')})
6. Implementa i breakpoint responsive: {css_analysis.get('responsive_breakpoints', [])}
"""
    
    # Salvare il prompt generato nello state
    tool_context.state["generated_replication_prompt"] = generated_prompt
    tool_context.state["prompt_generation_status"] = "completed"
    
    return {
        "status": "success", 
        "message": "Prompt per replica generato con successo",
        "prompt_length": len(generated_prompt),
        "data_points_processed": len(str(scraping_data))
    }

# ===== AGENTS =====

# 1. SCRAPING AGENT
scraping_agent = LlmAgent(
    model='gemini-2.0-flash',
    name='playwright_automation_agent',
    instruction=prompt.WEB_SCRAPING_AGENT_PROMPT,
    output_key='complete_site_data',  # Salva i dati di scraping qui
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='npx',
                args=[
                    "-y",  # Auto-confirm install
                    "@executeautomation/playwright-mcp-server"
                ],
            ),
        )
    ],
)

# 2. PROMPT GENERATOR AGENT
prompt_generator_agent = LlmAgent(
    model='gemini-2.0-flash',
    name="prompt_generator",
    instruction="""
    Sei specializzato nella generazione di prompt per la replica di siti web.
    
    Il tuo compito:
    1. Accedi ai dati di scraping completi da state['complete_site_data']
    2. Analizza tutti i componenti: design, struttura, contenuti, funzionalità
    3. Genera un prompt dettagliato e strutturato per replicare il sito
    
    Usa il tool generate_replication_prompt per processare i dati di scraping
    e creare un prompt completo che includa:
    - Design system (colori, typography, spacing)
    - Struttura HTML delle sezioni principali  
    - Elementi interattivi e funzionalità
    - Istruzioni specifiche per la replica
    
    Fornisci sempre un riepilogo di cosa è stato processato e generato.
    """,
    output_key="prompt_generation_summary",  # Salva il summary finale
    tools=[generate_replication_prompt]
)

# 3. SCRAPING TO PROMPT PIPELINE
scraping_pipeline = SequentialAgent(
    name="scraping_to_prompt_pipeline",
    sub_agents=[scraping_agent, prompt_generator_agent],
    description="Pipeline che esegue scraping completo e genera prompt per replica"
)

# 4. MANAGER AGENT (ROOT)
manager_agent = LlmAgent(
    model='gemini-2.0-flash',
    name='site_replication_manager',
    description='gestisci il workflow di replica siti web',
    instruction="""
    Sei un manager specializzato nella gestione del workflow di replica siti web.
    
    Quando l'utente richiede la replica di un sito web:
    
    1. COMPRENDI LA RICHIESTA
       - Identifica l'URL del sito target
       - Chiarisci eventuali requisiti specifici
    
    2. AVVIA IL PROCESSO
       - Usa la pipeline di scraping e generazione prompt
       - Monitora il progresso di ogni fase
    
    3. FORNISCI FEEDBACK
       - Aggiorna l'utente sui progressi
       - Segnala eventuali problemi o limitazioni
       - Presenta i risultati finali
    
    4. GESTISCI I RISULTATI
       - Verifica che tutti i dati siano stati raccolti
       - Assicurati che il prompt sia stato generato correttamente
       - Fornisci il prompt finale all'utente
    
    Hai accesso alla pipeline completa che include:
    - Scraping con Playwright MCP
    - Generazione prompt strutturato
    
    Mantieni sempre un tono professionale e fornisci update chiari sul processo.
    """,
    tools=[scraping_pipeline]  # Pipeline come strumento principale
)

# ===== ROOT AGENT FOR ADK =====
root_agent = manager_agent