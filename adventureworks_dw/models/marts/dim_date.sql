   with days as (

       select
           date_day,
           (datepart(weekday, date_day) + @@datefirst - 2) % 7 + 1 as day_of_week
       from {{ ref('stg_calendar') }}

   )

   select
       cast(format(date_day, 'yyyyMMdd') as int)       as date_key,
       date_day                                        as full_date,
       year(date_day)                                  as year,
       datepart(quarter, date_day)                     as quarter,
       concat(year(date_day), '-Q', datepart(quarter, date_day)) as year_quarter,
       month(date_day)                                 as month_number,
       datename(month, date_day)                       as month_name,
       format(date_day, 'yyyy-MM')                     as year_month,
       day(date_day)                                   as day_of_month,
       day_of_week,
       datename(weekday, date_day)                     as day_name,
       cast(case when day_of_week in (6, 7) then 1 else 0 end as bit) as is_weekend
   from days