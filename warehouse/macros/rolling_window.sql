{% macro rolling_feature(column, partition_col, order_col, window_days, aggregation='sum') %}
    {{ aggregation }}({{ column }}) over (
        partition by {{ partition_col }}
        order by {{ order_col }}
        range between interval '{{ window_days }} days' preceding
                  and interval '1 microsecond' preceding
    )
{% endmacro %}

