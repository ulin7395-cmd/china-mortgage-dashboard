"""Plotly 图表工厂"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

import plotly.io as pio
from config.settings import COLORS

# 自定义 Plotly 主题
pio.templates["loan_dashboard_light"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family="sans-serif", color="#333"),
        title_font=dict(size=20, color="#333"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            gridcolor="#e0e0e0",
            linecolor="#e0e0e0",
            zerolinecolor="#e0e0e0",
            tickfont=dict(color="#666"),
            title_font=dict(color="#666"),
        ),
        yaxis=dict(
            gridcolor="#e0e0e0",
            linecolor="#e0e0e0",
            zerolinecolor="#e0e0e0",
            tickfont=dict(color="#666"),
            title_font=dict(color="#666"),
        ),
        legend=dict(
            font=dict(color="#666"),
            bgcolor="rgba(255,255,255,0.5)",
            bordercolor="#e0e0e0",
            borderwidth=1,
        ),
        colorway=px.colors.qualitative.Plotly,
    )
)

pio.templates["loan_dashboard_dark"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family="sans-serif", color="#fafafa"),
        title_font=dict(size=20, color="#fafafa"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            gridcolor="#444",
            linecolor="#444",
            zerolinecolor="#444",
            tickfont=dict(color="#aaa"),
            title_font=dict(color="#aaa"),
        ),
        yaxis=dict(
            gridcolor="#444",
            linecolor="#444",
            zerolinecolor="#444",
            tickfont=dict(color="#aaa"),
            title_font=dict(color="#aaa"),
        ),
        legend=dict(
            font=dict(color="#aaa"),
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor="#444",
            borderwidth=1,
        ),
        colorway=px.colors.qualitative.Plotly,
    )
)

# 设置默认主题
pio.templates.default = "loan_dashboard_light"



def _get_x_labels(schedule: pd.DataFrame) -> list:
    """生成横轴标签，格式为「第N期 YYYY-MM」"""
    labels = []
    for _, row in schedule.iterrows():
        period = int(row["period"])
        due_date = row.get("due_date", "")
        if due_date:
            # 确保日期格式正确
            if isinstance(due_date, str):
                date_str = due_date[:7]  # 只取 YYYY-MM
            else:
                date_str = due_date.strftime("%Y-%m")
            labels.append(f"第{period}期 {date_str}")
        else:
            labels.append(f"第{period}期")
    return labels


def create_pie_chart(
    labels: list,
    values: list,
    title: str = "",
    colors: list = None,
    hole: float = 0.45,
    template: str = "loan_dashboard_light",
) -> go.Figure:
    """环形图"""
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=hole,
        marker_colors=colors or [COLORS["paid"], COLORS["unpaid"], COLORS["principal"], COLORS["interest"]],
        textinfo="label+percent",
        textposition="outside",
    )])
    fig.update_layout(
        title=title,
        showlegend=True,
        margin=dict(t=60, b=20, l=20, r=20),
        height=380,
        template=template,
    )
    return fig


def create_principal_interest_pie(
    paid_principal: float,
    paid_interest: float,
    unpaid_principal: float,
    unpaid_interest: float,
    template: str = "loan_dashboard_light",
) -> go.Figure:
    """已还/未还本金利息环形图"""
    fig = go.Figure(data=[go.Pie(
        labels=["已还本金", "已还利息", "未还本金", "未还利息"],
        values=[paid_principal, paid_interest, unpaid_principal, unpaid_interest],
        hole=0.45,
        marker_colors=[COLORS["principal"], COLORS["interest"], "#aec7e8", "#ffbb78"],
        textinfo="label+percent",
        textposition="outside",
    )])
    fig.update_layout(
        title="本金/利息构成",
        showlegend=True,
        margin=dict(t=60, b=20, l=20, r=20),
        height=400,
        template=template,
    )
    return fig


def create_monthly_payment_line(
    schedule: pd.DataFrame,
    prepayment_periods: list = None,
    rate_change_periods: list = None,
    template: str = "loan_dashboard_light",
) -> go.Figure:
    """月供趋势折线图"""
    fig = go.Figure()
    x_labels = _get_x_labels(schedule)

    fig.add_trace(go.Scatter(
        x=x_labels,
        y=schedule["monthly_payment"],
        mode="lines",
        name="月供",
        line=dict(color=COLORS["primary"], width=2),
        hovertemplate="%{x}<br>月供: %{y:,.2f}元<extra></extra>",
    ))

    # 标注提前还款点
    if prepayment_periods:
        period_to_idx = {int(row["period"]): idx for idx, (_, row) in enumerate(schedule.iterrows())}
        pp_data = schedule[schedule["period"].isin(prepayment_periods)]
        pp_x_labels = [x_labels[period_to_idx[int(p)]] for p in pp_data["period"] if int(p) in period_to_idx]
        pp_data = pp_data[pp_data["period"].apply(lambda p: int(p) in period_to_idx)]
        fig.add_trace(go.Scatter(
            x=pp_x_labels,
            y=pp_data["monthly_payment"],
            mode="markers",
            name="提前还款",
            marker=dict(color=COLORS["danger"], size=12, symbol="star"),
        ))

    # 标注利率调整点
    if rate_change_periods:
        period_to_idx = {int(row["period"]): idx for idx, (_, row) in enumerate(schedule.iterrows())}
        rc_data = schedule[schedule["period"].isin(rate_change_periods)]
        rc_x_labels = [x_labels[period_to_idx[int(p)]] for p in rc_data["period"] if int(p) in period_to_idx]
        rc_data = rc_data[rc_data["period"].apply(lambda p: int(p) in period_to_idx)]
        fig.add_trace(go.Scatter(
            x=rc_x_labels,
            y=rc_data["monthly_payment"],
            mode="markers",
            name="利率调整",
            marker=dict(color=COLORS["warning"], size=12, symbol="diamond"),
        ))

    fig.update_layout(
        title="月供趋势",
        xaxis_title="期数",
        yaxis_title="金额(元)",
        hovermode="x unified",
        margin=dict(t=60, b=60, l=60, r=20),
        height=400,
        xaxis=dict(
            tickmode="auto",
            nticks=15,
            tickangle=45,
        ),
        template=template,
    )
    return fig


def create_stacked_area(schedule: pd.DataFrame, template: str = "loan_dashboard_light") -> go.Figure:
    """本金/利息构成堆叠面积图"""
    fig = go.Figure()
    x_labels = _get_x_labels(schedule)

    fig.add_trace(go.Scatter(
        x=x_labels,
        y=schedule["principal"],
        mode="lines",
        name="本金",
        stackgroup="payment",
        line=dict(color=COLORS["principal"]),
        hovertemplate="%{x}<br>本金: %{y:,.2f}元<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=x_labels,
        y=schedule["interest"],
        mode="lines",
        name="利息",
        stackgroup="payment",
        line=dict(color=COLORS["interest"]),
        hovertemplate="%{x}<br>利息: %{y:,.2f}元<extra></extra>",
    ))

    fig.update_layout(
        title="每期本金/利息构成",
        xaxis_title="期数",
        yaxis_title="金额(元)",
        hovermode="x unified",
        margin=dict(t=60, b=60, l=60, r=20),
        height=400,
        xaxis=dict(
            tickmode="auto",
            nticks=15,
            tickangle=45,
        ),
        template=template,
    )
    return fig


def create_remaining_principal_line(schedule: pd.DataFrame, prepayment_periods: list = None, template: str = "loan_dashboard_light") -> go.Figure:
    """剩余本金下降曲线"""
    fig = go.Figure()
    x_labels = _get_x_labels(schedule)

    fig.add_trace(go.Scatter(
        x=x_labels,
        y=schedule["remaining_principal"],
        mode="lines",
        name="剩余本金",
        fill="tozeroy",
        line=dict(color=COLORS["primary"], width=2),
        fillcolor="rgba(31, 119, 180, 0.15)",
        hovertemplate="%{x}<br>剩余本金: %{y:,.2f}元<extra></extra>",
    ))

    # 标注提前还款点
    if prepayment_periods:
        period_to_idx = {int(row["period"]): idx for idx, (_, row) in enumerate(schedule.iterrows())}
        pp_data = schedule[schedule["period"].isin(prepayment_periods)]
        pp_x_labels = [x_labels[period_to_idx[int(p)]] for p in pp_data["period"] if int(p) in period_to_idx]
        pp_data = pp_data[pp_data["period"].apply(lambda p: int(p) in period_to_idx)]
        fig.add_trace(go.Scatter(
            x=pp_x_labels,
            y=pp_data["remaining_principal"],
            mode="markers",
            name="提前还款",
            marker=dict(color=COLORS["danger"], size=12, symbol="star"),
        ))

    fig.update_layout(
        title="剩余本金变化",
        xaxis_title="期数",
        yaxis_title="剩余本金(元)",
        hovermode="x unified",
        margin=dict(t=60, b=60, l=60, r=20),
        height=400,
        xaxis=dict(
            tickmode="auto",
            nticks=15,
            tickangle=45,
        ),
        template=template,
    )
    return fig


def create_cumulative_chart(schedule: pd.DataFrame, template: str = "loan_dashboard_light") -> go.Figure:
    """累计本金/利息曲线"""
    fig = go.Figure()
    x_labels = _get_x_labels(schedule)

    fig.add_trace(go.Scatter(
        x=x_labels,
        y=schedule["cumulative_principal"],
        mode="lines",
        name="累计本金",
        line=dict(color=COLORS["principal"], width=2),
        hovertemplate="%{x}<br>累计本金: %{y:,.2f}元<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=x_labels,
        y=schedule["cumulative_interest"],
        mode="lines",
        name="累计利息",
        line=dict(color=COLORS["interest"], width=2),
        hovertemplate="%{x}<br>累计利息: %{y:,.2f}元<extra></extra>",
    ))

    fig.update_layout(
        title="累计还款",
        xaxis_title="期数",
        yaxis_title="金额(元)",
        hovermode="x unified",
        margin=dict(t=60, b=60, l=60, r=20),
        height=400,
        xaxis=dict(
            tickmode="auto",
            nticks=15,
            tickangle=45,
        ),
        template=template,
    )
    return fig


def create_comparison_bar(comparison_df: pd.DataFrame, template: str = "loan_dashboard_light") -> go.Figure:
    """方案对比柱状图"""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="总还款额",
        x=comparison_df["方案名称"],
        y=comparison_df["总还款额"],
        marker_color=COLORS["primary"],
    ))

    fig.add_trace(go.Bar(
        name="总利息",
        x=comparison_df["方案名称"],
        y=comparison_df["总利息"],
        marker_color=COLORS["interest"],
    ))

    fig.update_layout(
        title="方案对比",
        barmode="group",
        yaxis_title="金额(元)",
        margin=dict(t=60, b=40, l=60, r=20),
        height=400,
        template=template,
    )
    return fig


def create_multi_schedule_line(
    schedules: dict,
    y_col: str = "monthly_payment",
    title: str = "月供对比",
    y_label: str = "金额(元)",
    template: str = "loan_dashboard_light",
) -> go.Figure:
    """多方案叠加折线图"""
    fig = go.Figure()
    colors = list(COLORS.values())

    for i, (name, sch) in enumerate(schedules.items()):
        x_labels = _get_x_labels(sch)
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=sch[y_col],
            mode="lines",
            name=name,
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate="%{x}<br>%{y:,.2f}元<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        xaxis_title="期数",
        yaxis_title=y_label,
        hovermode="x unified",
        margin=dict(t=60, b=60, l=60, r=20),
        height=400,
        xaxis=dict(
            tickmode="auto",
            nticks=15,
            tickangle=45,
        ),
        template=template,
    )
    return fig


def create_multi_principal_interest_area(
    schedules: dict,
    title: str = "每期本金与利息对比",
    template: str = "loan_dashboard_light",
) -> go.Figure:
    """多方案每期本金与利息对比（堆叠面积图）"""
    fig = go.Figure()
    colors = list(COLORS.values())
    color_pairs = [
        (COLORS["commercial"], "#aec7e8"),
        (COLORS["provident"], "#98df8a"),
        (COLORS["secondary"], "#ffbb78"),
        (COLORS["info"], "#c5b0d5"),
    ]

    for i, (name, sch) in enumerate(schedules.items()):
        x_labels = _get_x_labels(sch)
        color_idx = i % len(color_pairs)
        principal_color, interest_color = color_pairs[color_idx]

        # 添加本金
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=sch["principal"],
            mode="lines",
            name=f"{name} - 本金",
            stackgroup=f"group_{i}",
            line=dict(color=principal_color),
            hovertemplate="%{x}<br>本金: %{y:,.2f}元<extra></extra>",
        ))

        # 添加利息
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=sch["interest"],
            mode="lines",
            name=f"{name} - 利息",
            stackgroup=f"group_{i}",
            line=dict(color=interest_color),
            hovertemplate="%{x}<br>利息: %{y:,.2f}元<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        xaxis_title="期数",
        yaxis_title="金额(元)",
        hovermode="x unified",
        margin=dict(t=60, b=60, l=60, r=20),
        height=450,
        xaxis=dict(
            tickmode="auto",
            nticks=15,
            tickangle=45,
        ),
        template=template,
    )
    return fig


def create_separate_principal_interest_lines(
    schedules: dict,
    title: str = "本金与利息对比",
    template: str = "loan_dashboard_light",
) -> go.Figure:
    """多方案分开显示本金和利息折线图"""
    fig = go.Figure()
    colors = list(COLORS.values())

    for i, (name, sch) in enumerate(schedules.items()):
        x_labels = _get_x_labels(sch)
        color_idx = i * 2 % len(colors)

        # 添加本金
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=sch["principal"],
            mode="lines",
            name=f"{name} - 本金",
            line=dict(color=colors[color_idx], width=2, dash="solid"),
            hovertemplate="%{x}<br>本金: %{y:,.2f}元<extra></extra>",
        ))

        # 添加利息
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=sch["interest"],
            mode="lines",
            name=f"{name} - 利息",
            line=dict(color=colors[(color_idx + 1) % len(colors)], width=2, dash="dash"),
            hovertemplate="%{x}<br>利息: %{y:,.2f}元<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        xaxis_title="期数",
        yaxis_title="金额(元)",
        hovermode="x unified",
        margin=dict(t=60, b=60, l=60, r=20),
        height=450,
        xaxis=dict(
            tickmode="auto",
            nticks=15,
            tickangle=45,
        ),
        template=template,
    )
    return fig
