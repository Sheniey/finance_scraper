# ================================================== #
# MODULE: logging
# ================================================== #



TICKER_ADDED_TO_WATCHLIST = 'The ticker {ticker} was added to the watchlist of account {account} successfully.'
NO_ACCOUNT_PROVIDED     = 'No account information provided. Using default account ("testing").'
NO_ACCOUNT_FOUND        = 'No account was found.'
ACCOUNT_ALREADY_EXISTS  = 'An account with the email "{email}" already exists.'

TICKER_NOT_FOUND        = 'The specified ticker was not found.'

LLM_INITIALIZATION_FAILED = 'Failed to initialize the language model.'
LLM_PROVIDER_ERROR      = 'An error occurred with the language model provider.'
LLM_IS_UNAVAILABLE      = 'The language model is unavailable.'
INVALID_PROVIDER_PRIORITY = 'The provider priority configuration is invalid.'
INVALID_LLM_PROMPT      = 'The provided prompt is invalid.'
INVALID_LLM_EXPLANATION = 'The explanation returned by the language model is invalid.'
EMPTY_LLM_EXPLANATION   = 'The language model returned an empty explanation.'

ACCOUNT_SERVICE_ERROR   = 'The account service could not provide the required data.'
STOCK_ANALYZER_ERROR    = 'The stock analyzer could not complete the analysis for {ticker}.'
NEWS_EXTRACTOR_ERROR    = 'The news extractor could not retrieve news for {ticker}.'
ML_PREDICTION_ERROR     = 'The machine learning service could not predict an action for {ticker}.'
REPORT_CONFIGURATION_ERROR = 'The report configuration is invalid.'

MAKING_REQUESTS         = 'Making all pending watchlist requests and resolving them...'
REQUESTS_RESOLVED       = 'All pending watchlist requests have been resolved with the status {status}.'

GENERATING_REPORT       = 'Generating report for {symbol} to {renderer}...'
EMAIL_SENT              = 'The report for {symbol} was sent to {email}.'
EMAIL_DELIVERY_FAILED   = 'The report could not be sent by email.'
LOADING_ACCOUNT_PREFERENCES = 'Loading account preferences for account {account}...'
ANALYZING_TICKER        = 'Analyzing {ticker}...'
FETCHING_LATEST_NEWS    = 'Fetching latest news for {ticker}...'
PREDICTING_BEST_ACTION  = 'Predicting the best action for {ticker}...'
GENERATING_EXPLANATION  = 'Generating an explanation for the predicted action...'
EXPLANATION_GENERATED   = 'The explanation was generated successfully.'
EXPLANATION_DEGRADED    = 'The report was generated without an explanation.'

RENDERER_NOT_SUPPORTED  = 'Unsupported renderer. The available renderers are: console, pdf, page, site, txt, json, yaml, email.'

UNKNOWN_ERROR           = 'An unknown error occurred.'

LOG_INFO_STYLE          = 'log:info'
LOG_WARNING_STYLE       = 'log:warning'
LOG_ERROR_STYLE         = 'log:error'
LOG_DEBUG_STYLE         = 'log:debug'
