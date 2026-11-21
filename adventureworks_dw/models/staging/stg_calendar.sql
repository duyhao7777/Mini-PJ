   select
       try_convert(date, _date, 23) as date_day
   from {{ source('stg', 'calendar') }}