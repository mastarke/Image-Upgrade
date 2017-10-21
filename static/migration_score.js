Highcharts.chart('container', {
    chart: {
        type:'line'
    },
    credits: {
        enabled: false
    },
    title: {
        text: 'Merit Migration Score'
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
                        window.location.href = '/merit_table/' + tableDate;

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
