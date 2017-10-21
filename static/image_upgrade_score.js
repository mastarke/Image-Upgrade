Highcharts.chart('container', {
    chart: {
        type: 'column'
    },
    title: {
        text: 'Merit Upgrade Score ' + os_type
    },
    xAxis: {
        categories: score_date,
        crosshair: true
    },
    yAxis: {
        min: 0,
        title: {
            text: 'Score Value'
        }
    },
    credits: {
      enabled: false,
      text: 'mastarke'
    },
    tooltip: {
        headerFormat: '<span style="font-size:10px">{point.key}</span><table>',
        pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
            '<td style="padding:0"><b>{point.y:1f}</b></td></tr>',
        footerFormat: '</table>',
        shared: false,
        useHTML: true
    },
    plotOptions: {
        series: {
            cursor: 'pointer',
            point: {
                events: {
                    click: function() {
                        var tableDate = this.category;
                        console.log('Matthew click os_type is ' + os_type)
                        window.location.href = '/merit_table/' + tableDate + '/' + os_type + '/' + 0;

                    }
                }
            }
        }
    },
    series: [{
        name: 'Traffic Score',
        data: traffic_score

    }, {
        name: 'Trigger Score',
        data: psat_score

    }, {
        name: 'Final Score',
        data: final_score

    }]
});
