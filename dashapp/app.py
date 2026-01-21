"""Dash UI for RAG pipeline."""
import os
import sys
from typing import List, Dict, Any
import requests
from dash import Dash, html, dcc, Input, Output, State, ctx, ALL
import dash_bootstrap_components as dbc
from loguru import logger
import json

# Configuration
def _default_retrieval_api_url() -> str:
    """Choose default API URL based on OS."""
    if os.name == "nt":
        return "http://ecotech:8073"
    return "http://retrieval:8073"


RETRIEVAL_API_URL = os.getenv("RETRIEVAL_API_URL", _default_retrieval_api_url())
DASH_DEBUG = os.getenv("DASH_DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level=LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)

# Initialize Dash app
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    title="RAG - Manufacturing Documentation",
    suppress_callback_exceptions=True
)

# App layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1([
                html.I(className="fas fa-book-open me-3"),
                "Manufacturing Documentation RAG"
            ], className="text-primary mb-0"),
            html.P(
                "Search and retrieve information from equipment manuals",
                className="text-muted"
            )
        ])
    ], className="mb-4 mt-4"),
    
    # Search section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Search Documentation", className="mb-3"),
                    
                    # Query input
                    dbc.InputGroup([
                        dbc.Input(
                            id="query-input",
                            placeholder="e.g., How to calibrate PTL007?",
                            type="text",
                            debounce=True
                        ),
                        dbc.Button(
                            [html.I(className="fas fa-search me-2"), "Search"],
                            id="search-button",
                            color="primary"
                        )
                    ], className="mb-3"),
                    
                    # Advanced options
                    dbc.Collapse([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Number of Results"),
                                dbc.Input(
                                    id="top-k-input",
                                    type="number",
                                    value=5,
                                    min=1,
                                    max=20
                                )
                            ], width=4),
                            
                            dbc.Col([
                                dbc.Label("Hybrid Alpha (0=BM25, 1=Vector)"),
                                dbc.Input(
                                    id="alpha-input",
                                    type="number",
                                    value=0.5,
                                    min=0,
                                    max=1,
                                    step=0.1
                                )
                            ], width=4),
                            
                            dbc.Col([
                                dbc.Label("Reranking"),
                                dbc.Checklist(
                                    options=[{"label": "Enable", "value": 1}],
                                    value=[1],
                                    id="rerank-toggle",
                                    switch=True
                                )
                            ], width=4),
                        ])
                    ], id="advanced-options", is_open=False),
                    
                    dbc.Button(
                        "Advanced Options",
                        id="toggle-advanced",
                        color="link",
                        size="sm",
                        className="mt-2"
                    )
                ])
            ])
        ])
    ], className="mb-4"),
    
    # Loading indicator
    dbc.Row([
        dbc.Col([
            dcc.Loading(
                id="loading",
                type="default",
                children=html.Div(id="loading-output")
            )
        ])
    ]),
    
    # Results section
    dbc.Row([
        dbc.Col([
            html.Div(id="results-container")
        ])
    ]),
    
    # Store for results data
    dcc.Store(id="results-store"),
    
], fluid=True, className="py-4")


# Callbacks

@app.callback(
    Output("advanced-options", "is_open"),
    Input("toggle-advanced", "n_clicks"),
    State("advanced-options", "is_open"),
    prevent_initial_call=True
)
def toggle_advanced_options(n_clicks, is_open):
    """Toggle advanced options."""
    return not is_open


@app.callback(
    [
        Output("results-container", "children"),
        Output("results-store", "data"),
        Output("loading-output", "children")
    ],
    [
        Input("search-button", "n_clicks"),
        Input("query-input", "n_submit")
    ],
    [
        State("query-input", "value"),
        State("top-k-input", "value"),
        State("alpha-input", "value"),
        State("rerank-toggle", "value")
    ],
    prevent_initial_call=True
)
def perform_search(n_clicks, n_submit, query, top_k, alpha, rerank_value):
    """Perform search and display results."""
    if not query or query.strip() == "":
        return [
            dbc.Alert("Please enter a search query", color="warning"),
            None,
            None
        ]
    
    logger.info(f"Searching for: {query}")
    
    try:
        # Build request
        rerank = len(rerank_value) > 0 if rerank_value else False
        
        payload = {
            "query": query,
            "top_k": int(top_k),
            "rerank": rerank,
            "rerank_top_k": int(top_k),
            "alpha": float(alpha)
        }
        
        # Call API
        response = requests.post(
            f"{RETRIEVAL_API_URL}/query",
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            return [
                dbc.Alert(
                    f"Error: {response.status_code} - {response.text}",
                    color="danger"
                ),
                None,
                None
            ]
        
        data = response.json()
        results = data.get("results", [])
        processing_time = data.get("processing_time")
        total_results = data.get("total_results", 0)
        reranked = data.get("reranked", False)
        
        if not results:
            return [
                dbc.Alert(
                    "No results found. Try a different query or adjust search parameters.",
                    color="info"
                ),
                None,
                None
            ]
        
        # Build results UI
        results_ui = build_results_ui(
            query=query,
            results=results,
            total=total_results,
            processing_time=processing_time,
            reranked=reranked
        )
        
        return [results_ui, data, None]
        
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to retrieval API")
        return [
            dbc.Alert(
                "Failed to connect to retrieval service. Please ensure the service is running.",
                color="danger"
            ),
            None,
            None
        ]
    except Exception as e:
        logger.error(f"Search error: {e}")
        return [
            dbc.Alert(f"Error: {str(e)}", color="danger"),
            None,
            None
        ]


def build_results_ui(
    query: str,
    results: List[Dict[str, Any]],
    total: int,
    processing_time: float,
    reranked: bool
) -> html.Div:
    """Build results UI."""
    
    # Summary card
    summary = dbc.Card([
        dbc.CardBody([
            html.H5("Search Results", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-search fa-2x text-primary mb-2"),
                        html.H6("Query", className="text-muted"),
                        html.P(query, className="mb-0")
                    ])
                ], width=4),
                
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-list fa-2x text-success mb-2"),
                        html.H6("Results", className="text-muted"),
                        html.P(f"{total} passages", className="mb-0")
                    ])
                ], width=4),
                
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-clock fa-2x text-info mb-2"),
                        html.H6("Processing Time", className="text-muted"),
                        html.P(f"{processing_time:.2f}s" if processing_time is not None else "N/A", className="mb-0")
                    ])
                ], width=4),
            ]),
            
            html.Hr(),
            
            dbc.Badge(
                [html.I(className="fas fa-check me-1"), "Reranked"],
                color="success",
                className="me-2"
            ) if reranked else None,
            
            dbc.Badge(
                [html.I(className="fas fa-robot me-1"), "Hybrid Search (BM25 + Vector)"],
                color="info"
            )
        ])
    ], className="mb-4")
    
    # Result cards
    result_cards = []
    for i, result in enumerate(results, 1):
        card = create_result_card(result, i)
        result_cards.append(card)
    
    return html.Div([
        summary,
        html.Div(result_cards)
    ])


def create_result_card(result: Dict[str, Any], index: int) -> dbc.Card:
    """Create a result card."""
    
    # Extract data
    doc_id = result.get("doc_id", "Unknown")
    page = result.get("page", 0)
    text = result.get("text", "")
    section_path = result.get("section_path", "")
    score = result.get("score")
    
    # Format document name
    doc_title = doc_id.replace("_", " ").replace("Navodila ", "Manual: ")
    
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H6([
                        html.Span(f"#{index}", className="badge bg-primary me-2"),
                        html.I(className="fas fa-file-pdf me-2 text-danger"),
                        doc_title
                    ], className="mb-0")
                ], width=8),
                
                dbc.Col([
                    dbc.Badge(
                        f"Page {page}",
                        color="secondary",
                        className="me-2"
                    ),
                    dbc.Badge(
                        f"Score: {score:.3f}" if score is not None else "Score: N/A",
                        color="success"
                    )
                ], width=4, className="text-end")
            ])
        ]),
        
        dbc.CardBody([
            # Section path
            html.P([
                html.I(className="fas fa-sitemap me-2 text-muted"),
                html.Small(section_path, className="text-muted")
            ], className="mb-2") if section_path else None,
            
            # Content
            html.P(text, className="mb-3"),
            
            # Actions
            dbc.ButtonGroup([
                dbc.Button(
                    [html.I(className="fas fa-external-link-alt me-2"), "View Page"],
                    color="primary",
                    size="sm",
                    outline=True,
                    href=f"{RETRIEVAL_API_URL}/doc/{doc_id}/page/{page}",
                    target="_blank"
                ),
                dbc.Button(
                    [html.I(className="fas fa-copy me-2"), "Copy"],
                    color="secondary",
                    size="sm",
                    outline=True,
                    id={"type": "copy-button", "index": index}
                )
            ])
        ])
    ], className="mb-3")


# Run app
if __name__ == "__main__":
    if os.name == "nt":
        host = os.getenv("DASH_HOST", "127.0.0.1")
        port = int(os.getenv("DASH_PORT", 8050))
    else:
        host = os.getenv("DASH_HOST", "0.0.0.0")
        port = int(os.getenv("DASH_PORT", 8072))

    logger.info(f"Starting Dash app on {host}:{port}")
    logger.info(f"Retrieval API: {RETRIEVAL_API_URL}")

    app.run(
        host=host,
        port=port,
        debug=DASH_DEBUG
    )

