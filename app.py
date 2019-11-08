import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import plotly.graph_objects as go

from sqlalchemy import create_engine

df = pd.read_csv('aggr.csv', parse_dates=['Entry time'])

app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/uditagarwal/pen/oNvwKNP.css',
                                                'https://codepen.io/uditagarwal/pen/YzKbqyV.css'])

############################################
# Here goes the Layout of the dashboard
############################################

app.layout = html.Div(
    children=[
        html.Div(
            children=[
                html.H2(children="Bitcoin Leveraged Trading Backtest Analysis", className='h2-title'),
            ],
            className='study-browser-banner row'
        ),
        html.Div(
            className="row app-body",
            children=[
                html.Div(
                    className="twelve columns card",
                    children=[
                        html.Div(
                            className="padding row",
                            children=[
                                html.Div(
                                    className="two columns card",
                                    children=[
                                        html.H6("Select Exchange",),
                                        dcc.RadioItems(
                                            id="exchange-select",
                                            options=[
                                                {'label': label, 'value': label} for label in df['Exchange'].unique()
                                            ],
                                            value='Bitmex',
                                            labelStyle={'display': 'inline-block'}
                                        )
                                    ]
                                ),
                                html.Div(
                                    className="two columns card",
                                    children=[
                                        html.H6("Select Leverage",),
                                        dcc.RadioItems(
                                            id="leverage-select",
                                            options=[
                                                {'label': label, 'value': label} for label in df['Margin'].unique()
                                            ],
                                            value=1,
                                            labelStyle={'display': 'inline-block'}
                                        )
                                    ]
                                ),
                                html.Div(
                                    className="three columns card",
                                    children=[
                                        html.H6("Select a Date Range",),
                                        dcc.DatePickerRange(
                                            id="date-range-select",
                                            start_date=df['Entry time'].min(), # The start_date is going to be the min of Order Date in our dataset
                                            end_date=df['Entry time'].max(),
                                            display_format = 'MMM YY',
                                        )
                                    ]
                                ),
                                html.Div(
                                    id="strat-returns-div",
                                    className="two columns indicator pretty_container",
                                    children=[
                                        html.P(id="strat-returns", className="indicator_value"),
                                        html.P('Strategy Returns', className="twelve columns indicator_text"),
                                    ]
                                ),
                                html.Div(
                                    id="market-returns-div",
                                    className="two columns indicator pretty_container",
                                    children=[
                                        html.P(id="market-returns", className="indicator_value"),
                                        html.P('Market Returns', className="twelve columns indicator_text"),
                                    ]
                                ),
                                html.Div(
                                    id="strat-vs-market-div",
                                    className="two columns indicator pretty_container",
                                    children=[
                                        html.P(id="strat-vs-market", className="indicator_value"),
                                        html.P('Strategy vs. Market Returns', className="twelve columns indicator_text"),
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                html.Div(
                    className="twelve columns card",
                    children=[
                        dcc.Graph(
                            id="monthly-chart",
                            figure={
                                'data': []
                            }
                        )
                    ]
                ),
                html.Div(
                    className="padding row",
                    children=[
                        html.Div(
                            className="six columns card",
                            children=[
                                dash_table.DataTable(
                                    id='table',
                                    columns=[
                                        {'name': 'Number', 'id': 'Number'},
                                        {'name': 'Trade type', 'id': 'Trade type'},
                                        {'name': 'Exposure', 'id': 'Exposure'},
                                        {'name': 'Entry balance', 'id': 'Entry balance'},
                                        {'name': 'Exit balance', 'id': 'Exit balance'},
                                        {'name': 'Pnl (incl fees)', 'id': 'Pnl (incl fees)'},
                                    ],
                                    style_cell={'width': '50px'},
                                    style_table={
                                        'maxHeight': '450px',
                                        'overflowY': 'scroll'
                                    },
                                )
                            ]
                        ),
                        html.Div(
                            className="six columns card",
                            children=[
                                dcc.Graph(
                                    id="pnl-types",
                                    figure={
                                    }
                                )
                            ]
                        )  
                    ]
                ),
                html.Div(
                    className="padding row",
                    children=[
                        dcc.Graph(
                            id="daily-btc",
                            className="six columns card",
                            figure={}
                        ),
                        dcc.Graph(
                            id="balance",
                            className="six columns card",
                            figure={}
                        )
                    ]
                )
            ]
        )
    ]
)

############################################
# Here go all the needed functions
############################################

def filter_df(df, exchange, leverage, start_date, end_date):
    df = df.copy()
    mask_1 = df['Exchange'] == exchange
    mask_2 = df['Margin'] == leverage
    mask_3 = df['Entry time'] >= start_date
    mask_4 = df['Entry time'] <= end_date
    return df[mask_1 & mask_2 & mask_3 & mask_4]

def calc_returns_over_month(dff):
    dff = dff.copy()
    dff['YearMonth'] = dff['Entry time'] \
        .apply(lambda x: x.year * 100 + x.month)
    dff['YearMonth'] = pd.to_datetime(dff['YearMonth'], format='%Y%m')
    out = []
    for name, group in dff.groupby('YearMonth'):
        exit_balance = group.head(1)['Exit balance'].values[0]
        entry_balance = group.tail(1)['Entry balance'].values[0]
        monthly_return = (exit_balance*100 / entry_balance)-100
        out.append({
            'month': name,
            'entry': entry_balance,
            'exit': exit_balance,
            'monthly_return': monthly_return
        })
    return out

def calc_btc_returns(dff):
    btc_start_value = dff.tail(1)['BTC Price'].values[0]
    btc_end_value = dff.head(1)['BTC Price'].values[0]
    btc_returns = (btc_end_value * 100/ btc_start_value)-100
    return btc_returns

def calc_strat_returns(dff):
    start_value = dff.tail(1)['Exit balance'].values[0]
    end_value = dff.head(1)['Entry balance'].values[0]
    returns = (end_value * 100/ start_value)-100
    return returns

def category_bar_plot(df):
    data = []
    for name, group in df.groupby(['Trade type']):
        data.append(
            go.Bar(
                x = group['Entry time'], 
                y = group['Pnl (incl fees)'], 
                name=name
            )
        )
    return data

def line_plot(df, x, y, name):
    data = []
    data.append(
        go.Scatter(
            x = df[x], 
            y = df[y], 
            name=name
        )
    )
    return data

############################################
# Here go all the callback functions
############################################

@app.callback(
    (
        dash.dependencies.Output('date-range-select', 'start_date'),
        dash.dependencies.Output('date-range-select', 'end_date')
    ),
    (
        dash.dependencies.Input('exchange-select', 'value'),
    )
)
def update_dates(exchange):
    return (
        df.loc[df['Exchange']==exchange, 'Entry time'].min(),
        df.loc[df['Exchange']==exchange, 'Entry time'].max()
    )


@app.callback(
    (
        dash.dependencies.Output('monthly-chart', 'figure'),
        dash.dependencies.Output('market-returns', 'children'),
        dash.dependencies.Output('strat-returns', 'children'),
        dash.dependencies.Output('strat-vs-market', 'children'),
    ),
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range-select', 'start_date'),
        dash.dependencies.Input('date-range-select', 'end_date'),

    )
)
def update_monthly(exchange, leverage, start_date, end_date):
    dff = filter_df(df, exchange, leverage, start_date, end_date)
    data = calc_returns_over_month(dff)
    btc_returns = calc_btc_returns(dff)
    strat_returns = calc_strat_returns(dff)
    strat_vs_market = strat_returns - btc_returns

    return {
        'data': [
            go.Candlestick(
                open=[each['entry'] for each in data],
                close=[each['exit'] for each in data],
                x=[each['month'] for each in data],
                low=[each['entry'] for each in data],
                high=[each['exit'] for each in data]
            )
        ],
        'layout': {
            'title': 'Overview of Monthly performance'
        }
    }, f'{btc_returns:0.2f}%', f'{strat_returns:0.2f}%', f'{strat_vs_market:0.2f}%'


@app.callback(
    dash.dependencies.Output('table', 'data'),
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range-select', 'start_date'),
        dash.dependencies.Input('date-range-select', 'end_date'),
    )
)
def update_table(exchange, leverage, start_date, end_date):
    dff = filter_df(df, exchange, leverage, start_date, end_date)
    return dff.to_dict('records')


@app.callback(
    dash.dependencies.Output('pnl-types', 'figure'),
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range-select', 'start_date'),
        dash.dependencies.Input('date-range-select', 'end_date'),
    )
)
def update_bar_plot(exchange, leverage, start_date, end_date):
    dff = filter_df(df, exchange, leverage, start_date, end_date)

    return {
        'data': category_bar_plot(dff),
        'layout': {
            'title': 'Profits',
            'barmode': 'group'
        }
    }

@app.callback(
    dash.dependencies.Output('daily-btc', 'figure'),
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range-select', 'start_date'),
        dash.dependencies.Input('date-range-select', 'end_date'),
    )
)
def update_btc_plot(exchange, leverage, start_date, end_date):
    dff = filter_df(df, exchange, leverage, start_date, end_date)

    return {
        'data': line_plot(dff, 'Entry time', 'BTC Price', 'btc'),
        'layout': {
            'title': 'Daily BTC Price',
            'height': 400
        }
    }

@app.callback(
    dash.dependencies.Output('balance', 'figure'),
    (
        dash.dependencies.Input('exchange-select', 'value'),
        dash.dependencies.Input('leverage-select', 'value'),
        dash.dependencies.Input('date-range-select', 'start_date'),
        dash.dependencies.Input('date-range-select', 'end_date'),
    )
)
def update_returns_plot(exchange, leverage, start_date, end_date):
    dff = filter_df(df, exchange, leverage, start_date, end_date)
    dff['balance'] = dff['Exit balance'] + dff['Pnl (incl fees)']

    return {
        'data': line_plot(dff, 'Entry time', 'balance', 'balance'),
        'layout': {
            'title': 'Daily Balance',
            'height': 400
        }
    }

if __name__ == "__main__":
    app.run_server(debug=False, port=8080)