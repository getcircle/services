#! /bin/bash
eb create $1 --cname "$1-circleapp" --instance_type t1.micro --single --platform "Docker 1.3.3" --region "us-east-1" --database.password $2 --database.engine postgres --database.size 5 --tags "env=$1"
