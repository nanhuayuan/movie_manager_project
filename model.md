# 项目模型关系
## ER图
```angular2html

erDiagram
    MOVIE ||--o{ MOVIE_DIRECTOR : has
    MOVIE ||--o{ MOVIE_GENRE : has
    MOVIE ||--o{ MOVIE_LABEL : has
    MOVIE ||--o{ MOVIE_SERIES : has
    MOVIE ||--o{ MOVIE_STAR : has
    MOVIE ||--o{ MAGNET : has
    MOVIE ||--o{ CHART_ENTRY : appears_in
    MOVIE ||--o{ CHART_HISTORY : appears_in
    MOVIE }|--|| STUDIO : belongs_to
    DIRECTOR ||--o{ MOVIE_DIRECTOR : in
    GENRE ||--o{ MOVIE_GENRE : in
    LABEL ||--o{ MOVIE_LABEL : in
    SERIES ||--o{ MOVIE_SERIES : in
    STAR ||--o{ MOVIE_STAR : in
    CHART ||--o{ CHART_ENTRY : contains
    CHART ||--o{ CHART_HISTORY : has
    CHART }|--|| CHART_TYPE : has

    MOVIE {
        int id
        string name
        string censored_id
        string serial_number
        date release_date
        int length
        float score
    }

    DIRECTOR {
        int id
        string name
        date birthday
    }

    GENRE {
        int id
        string name
    }

    LABEL {
        int id
        string name
    }

    SERIES {
        int id
        string name
    }

    STAR {
        int id
        string name
        date birthday
        int age
        string cupsize
    }

    STUDIO {
        int id
        string name
    }

    MAGNET {
        int id
        string name
        string magnet_xt
        bigint size
        datetime date
    }

    CHART {
        int id
        string name
        string description
    }

    CHART_TYPE {
        int id
        string name
        string description
    }

    CHART_ENTRY {
        int id
        int rank
        float score
        int votes
        int status
    }

    CHART_HISTORY {
        int id
        int rank
        float score
        int votes
        datetime recorded_at
    }
```
## 解释每个表的含义以及关系
好的,我会为您解释每个表的含义以及它们之间的关系。

    Movie (电影表)
        这是核心表,存储了电影的基本信息。
        包含电影名称、识别码、发行日期、时长、评分等信息。
        与其他表有多种关系:
            一对多关系: 与 Studio、Magnet
            多对多关系: 与 Director、Genre、Label、Series、Star
    Director (导演表)
        存储导演的基本信息。
        与 Movie 表是多对多关系,通过 movie_director 中间表关联。
    Genre (类别表)
        存储电影类别信息。
        与 Movie 表是多对多关系,通过 movie_genre 中间表关联。
    Label (标签表)
        存储电影标签信息。
        与 Movie 表是多对多关系,通过 movie_label 中间表关联。
    Series (系列表)
        存储电影系列信息。
        与 Movie 表是多对多关系,通过 movie_series 中间表关联。
    Star (演员表)
        存储演员的详细信息,包括生日、年龄、三围等。
        与 Movie 表是多对多关系,通过 movie_star 中间表关联。
    Studio (制作商表)
        存储制作公司信息。
        与 Movie 表是一对多关系,一个制作商可以制作多部电影。
    Magnet (磁力链接表)
        存储与电影相关的磁力链接信息。
        与 Movie 表是多对一关系,一部电影可以有多个磁力链接。
    ChartType (榜单类型表)
        定义不同类型的榜单。
        与 Chart 表是一对多关系。
    Chart (榜单表)
        存储榜单的基本信息。
        与 ChartType 是多对一关系。
        与 ChartEntry 和 ChartHistory 是一对多关系。
    ChartEntry (榜单条目表)
        记录电影在榜单中的具体排名信息。
        与 Chart 和 Movie 都是多对一关系。
    ChartHistory (榜单历史表)
        记录榜单的历史变化。
        与 Chart 和 Movie 都是多对一关系。

关系总结:

    Movie 是核心实体,与多个其他实体有关联。
    Director、Genre、Label、Series、Star 与 Movie 都是多对多关系,需要中间表。
    Studio 与 Movie 是一对多关系。
    Magnet 与 Movie 是多对一关系。
    Chart 相关的表(ChartType、Chart、ChartEntry、ChartHistory)形成了一个榜单系统,用于跟踪电影的排名和历史变化。

这个数据库设计允许灵活地存储和查询电影相关的各种信息,包括基本详情、相关人员、分类、排名等,适合构建一个全面的电影信息系统。

##这些表你有什么优化建议吗
当然,我可以提供一些优化建议。以下是一些可能的改进方向:

    索引优化:
```angular2html
-- Movie 表
   CREATE INDEX idx_movie_release_date ON movie(release_date);
   CREATE INDEX idx_movie_score ON movie(score);
   CREATE INDEX idx_movie_censored_id ON movie(censored_id);
   
   -- Star 表
   CREATE INDEX idx_star_name ON star(name);
   CREATE INDEX idx_star_birthday ON star(birthday);
   
   -- Magnet 表
   CREATE INDEX idx_magnet_date ON magnet(date);
   CREATE INDEX idx_magnet_size ON magnet(size);
   
   -- ChartEntry 表
   CREATE INDEX idx_chart_entry_rank ON chart_entry(rank);
   
   -- ChartHistory 表
   CREATE INDEX idx_chart_history_recorded_at ON chart_history(recorded_at);
```

这些索引将有助于提高查询性能,特别是在按日期、评分、名称等常用字段进行搜索和排序时。
数据类型优化:

    对于 movie.length, 考虑使用 SMALLINT 而不是 INT,因为电影长度通常不会超过 32,767 分钟。
    对于布尔值字段(如 movie.have_mg, movie.have_file 等),考虑使用 BOOLEAN 类型而不是 TINYINT,这样更直观且可能更节省空间。

规范化:

    考虑将 star 表中的身体数据(身高、三围等)拆分到单独的表中,因为这些信息可能会随时间变化。

冗余数据处理:

    movie 表中的 name, name_cn, name_en 字段可能存在冗余。考虑创建一个单独的 movie_names 表来存储不同语言的电影名称。

枚举类型:

    对于状态字段(如 chart_entry.status),考虑使用 ENUM 类型而不是 INT,这样可以增加代码的可读性和数据的一致性。

分区:

    对于 chart_history 表,如果数据量很大,可以考虑按时间进行分区,以提高查询效率。

全文索引:

    对于 movie.title 字段,考虑添加全文索引以支持更好的搜索功能。

sql

ALTER TABLE movie ADD FULLTEXT INDEX idx_fulltext_title (title);

存储引擎选择:

    对于需要频繁更新的表(如 chart_entry),考虑使用 InnoDB 引擎。
    对于几乎不更新的表(如 genre),可以考虑使用 MyISAM 引擎以获得更好的读取性能。

外键约束:

    添加外键约束可以保证数据的一致性,但也可能影响性能。需要权衡数据一致性和性能需求。

压缩:

    对于较大的文本字段(如 movie.title),可以考虑使用压缩来节省存储空间。

垂直分割:

    如果某些字段(如详细描述)很少被访问,可以考虑将它们移到单独的表中,以提高主表的查询效率。

