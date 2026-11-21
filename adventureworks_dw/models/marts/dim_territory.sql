   select
       territory_key,
       region,
       country,
       continent
   from {{ ref('stg_territory') }}